
import json
import os
import ipaddress

import boto3
from botocore.exceptions import ClientError


cloudformation = boto3.client("cloudformation")

STACK_NAME = "self-service-asg-lab01"


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def lambda_handler(event, context):

    # Requests arriving through API Gateway must never
    # trigger infrastructure provisioning in this phase.
    if "requestContext" in event:
        method = event.get("requestContext", {}).get(
            "http", {}
        ).get("method")

        path = event.get("rawPath")

        if method == "GET" and path == "/health":
            return response(200, {
                "status": "healthy",
                "service": "aws-self-service-platform",
                "message": "API Gateway to Lambda integration works",
            })

        return response(404, {"error": "Not found"})

    # Only explicitly approved direct Lambda test events.
    if event.get("action") != "provision-test":
        return {"error": "Unsupported action"}

    try:
        ip = ipaddress.ip_address(event["publicIp"])

        if ip.version != 4 or not ip.is_global:
            return {"error": "A public IPv4 address is required"}

        allowed_cidr = f"{ip}/32"

    except (KeyError, ValueError, TypeError):
        return {"error": "Invalid public IPv4 address"}

    try:
        result = cloudformation.create_stack(
            StackName=STACK_NAME,
            TemplateURL=os.environ["TEMPLATE_URL"],
            RoleARN=os.environ["CFN_EXECUTION_ROLE_ARN"],
            Parameters=[
                {
                    "ParameterKey": "AllowedCidr",
                    "ParameterValue": allowed_cidr,
                },
                {
                    "ParameterKey": "InstanceType",
                    "ParameterValue": "t3.micro",
                },
            ],
            Tags=[
                {"Key": "Project", "Value": "AWS-Self-Service"},
                {"Key": "Environment", "Value": "Dev"},
            ],
            OnFailure="DELETE",
        )

        return {
            "status": "CREATE_REQUESTED",
            "stackName": STACK_NAME,
            "stackId": result["StackId"],
        }

    except ClientError as error:
        code = error.response["Error"]["Code"]
        return {
            "status": "CREATE_REQUEST_FAILED",
            "errorCode": code,
            "message": error.response["Error"]["Message"],
        }