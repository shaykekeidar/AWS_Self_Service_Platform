import json


def lambda_handler(event, context):
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "status": "healthy",
            "service": "aws-self-service-platform",
            "message": "API Gateway to Lambda integration works"
        })
    }