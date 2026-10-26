import ipaddress
import json
import os

import boto3
from botocore.exceptions import ClientError

cloudformation = boto3.client("cloudformation")

# Deliberately fixed for this single-stack POC: never user-controlled.
STACK_NAME = "self-service-asg-lab01"


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def stack_status():
    # Describe the one approved stack by its full name, never list arbitrary stacks.
    try:
        stack = cloudformation.describe_stacks(StackName=STACK_NAME)["Stacks"][0]
        return {
            "stackName": STACK_NAME,
            "stackId": stack["StackId"],
            "status": stack["StackStatus"],
        }
    except ClientError as error:
        if error.response["Error"]["Code"] == "ValidationError" and "does not exist" in error.response["Error"].get("Message", ""):
            return None
        raise


def provision(event_data):
    # publicIp is a manual POC input used to restrict ALB ingress.
    # Never trust or infer this value from arbitrary forwarded headers.
    try:
        ip = ipaddress.ip_address(event_data["publicIp"])
        if ip.version != 4 or not ip.is_global:
            return 400, {"error": "A public IPv4 address is required"}
        allowed_cidr = f"{ip}/32"
    except (KeyError, ValueError, TypeError):
        return 400, {"error": "Invalid public IPv4 address"}

    try:
        existing = stack_status()
        if existing:
            return 409, {"error": "Fixed POC stack already exists", **existing}

        result = cloudformation.create_stack(
            StackName=STACK_NAME,
            TemplateURL=os.environ["TEMPLATE_URL"],
            RoleARN=os.environ["CFN_EXECUTION_ROLE_ARN"],
            Parameters=[
                {"ParameterKey": "AllowedCidr", "ParameterValue": allowed_cidr},
                {"ParameterKey": "InstanceType", "ParameterValue": "t3.micro"},
            ],
            Tags=[
                {"Key": "Project", "Value": "AWS-Self-Service"},
                {"Key": "Environment", "Value": "Dev"},
            ],
            OnFailure="DELETE",
        )
        return 202, {
            "status": "CREATE_REQUESTED",
            "stackName": STACK_NAME,
            "stackId": result["StackId"],
        }
    except ClientError as error:
        # CloudFormation rejects duplicate names even if two requests race.
        code = error.response["Error"]["Code"]
        message = error.response["Error"].get("Message", "CloudFormation request failed")
        if code == "AlreadyExistsException" or (code == "ValidationError" and "already exists" in message.lower()):
            return 409, {"error": "Fixed POC stack already exists", "stackName": STACK_NAME}
        # Avoid returning raw AWS errors to browser clients.
        print(f"Provisioning failed: {code}: {message}")
        return 502, {"error": "CloudFormation provisioning request failed", "errorCode": code}


def lambda_handler(event, context):
    if "requestContext" in event:
        http = event.get("requestContext", {}).get("http", {})
        method, path = http.get("method"), event.get("rawPath")

        if method == "GET" and path == "/health":
            return response(200, {
                "status": "healthy",
                "service": "aws-self-service-platform",
                "message": "API Gateway to Lambda integration works",
            })

        # Defense in depth: API Gateway JWT authorizer is the primary guard.
        jwt = event.get("requestContext", {}).get("authorizer", {}).get("jwt")
        if (method, path) in {("POST", "/provision"), ("GET", "/stack")} and not jwt:
            return response(403, {"error": "Authorized user required"})

        if method == "GET" and path == "/stack":
            try:
                stack = stack_status()
                return response(200, stack or {"status": "NOT_FOUND", "stackName": STACK_NAME})
            except ClientError:
                return response(502, {"error": "Could not retrieve stack status"})

        if method == "POST" and path == "/provision":
            try:
                payload = json.loads(event.get("body") or "{}")
                if not isinstance(payload, dict):
                    raise ValueError("JSON object required")
            except (ValueError, TypeError):
                return response(400, {"error": "Invalid JSON request body"})
            status, body = provision(payload)
            return response(status, body)

        return response(404, {"error": "Not found"})

    # Preserve direct Lambda test operation. IAM controls who may invoke it.
    if event.get("action") != "provision-test":
        return {"error": "Unsupported action"}
    status, body = provision(event)
    return body
