# AWS Self-Service Platform

A CloudFormation-based AWS self-service infrastructure project designed to provision application environments using a reusable network, a serverless control plane, and independently managed EC2 Auto Scaling stacks.

## 1. Architecture Overview

The solution consists of three independent AWS CloudFormation stacks.

| Stack | Template | Purpose |
|---|---|---|
| `self-service-network` | `cloudformation/network/network.yaml` | VPC, public/private subnets, Internet Gateway, and routing |
| `self-service-platform` | `cloudformation/platform/platform.yaml` | API Gateway, Lambda, and Lambda IAM execution role |
| `self-service-asg-<request-id>` | `cloudformation/provisioning/asg.yaml` | ALB, security groups, launch template, EC2 Auto Scaling Group |

The stacks are independent rather than nested.

The network stack exports shared infrastructure identifiers that the provisioning stack imports.

The platform stack is intended to become the control plane for automated provisioning. Currently, application stacks are deployed manually using the AWS CLI.

## 2. Network Design

The project uses a dedicated VPC rather than the default AWS VPC.

| Component | CIDR |
|---|---|
| VPC | `10.50.0.0/16` |
| Public subnet A | `10.50.1.0/24` |
| Public subnet B | `10.50.2.0/24` |
| Private subnet A | `10.50.11.0/24` |
| Private subnet B | `10.50.12.0/24` |

The public subnets host the internet-facing Application Load Balancer.

The private subnets host EC2 instances managed by an Auto Scaling Group.

No NAT Gateway is configured. The application is initialized using Amazon Linux 2023 User Data and does not require internet downloads during startup.

## 3. Prerequisites

Before deploying, ensure the following tools and permissions are available:

- AWS CLI v2
- Configured AWS credentials and default Region
- CloudFormation, EC2, Elastic Load Balancing, Auto Scaling, Lambda, API Gateway, and IAM deployment permissions
- PowerShell or another compatible terminal

Run the following commands from the repository root:

```powershell
cd D:\git\AWS_Self_Service_Platform

aws sts get-caller-identity
aws configure get region
```

Ensure that the AWS account and Region are correct before deployment.

## 4. Validate CloudFormation Templates

Validate each template before creating resources.

```powershell
aws cloudformation validate-template `
  --template-body file://cloudformation/network/network.yaml

aws cloudformation validate-template `
  --template-body file://cloudformation/platform/platform.yaml

aws cloudformation validate-template `
  --template-body file://cloudformation/provisioning/asg.yaml
```

Successful validation confirms CloudFormation template syntax and basic structure. It does not guarantee that deployment will succeed.

## 5. Deploy Stack 1 — Network

Deploy the network infrastructure first.

```powershell
aws cloudformation deploy `
  --template-file cloudformation/network/network.yaml `
  --stack-name self-service-network `
  --tags Project=AWS-Self-Service Environment=Dev
```

Verify deployment:

```powershell
aws cloudformation describe-stacks `
  --stack-name self-service-network `
  --query "Stacks[0].StackStatus"
```

Expected status:

`CREATE_COMPLETE` or `UPDATE_COMPLETE`

View the network exports:

```powershell
aws cloudformation list-exports `
  --query "Exports[?starts_with(Name, 'self-service-')]"
```

Expected exports include:

- `self-service-vpc-id`
- `self-service-public-subnet-a`
- `self-service-public-subnet-b`
- `self-service-private-subnet-a`
- `self-service-private-subnet-b`

These exports are used by the provisioning stack.

## 6. Deploy Stack 2 — Platform

Deploy the API Gateway and Lambda control plane.

```powershell
aws cloudformation deploy `
  --template-file cloudformation/platform/platform.yaml `
  --stack-name self-service-platform `
  --capabilities CAPABILITY_IAM `
  --tags Project=AWS-Self-Service Environment=Dev
```

Verify:

```powershell
aws cloudformation describe-stacks `
  --stack-name self-service-platform `
  --query "Stacks[0].StackStatus"
```

Retrieve the stack outputs:

```powershell
aws cloudformation describe-stacks `
  --stack-name self-service-platform `
  --query "Stacks[0].Outputs"
```

Locate the API Gateway endpoint and test its health route:

```powershell
Invoke-RestMethod -Uri "https://YOUR_API_ENDPOINT/health"
```

Expected response:

```json
{
  "status": "healthy",
  "service": "aws-self-service-platform",
  "message": "API Gateway to Lambda integration works"
}
```

**Implementation note:** The deployed Lambda currently uses inline Python code defined in `platform.yaml`. The separate `lambda/platform/app.py` file is not yet used as the deployment source.

## 7. Deploy Stack 3 — Application Environment

Each application environment is deployed as its own independent CloudFormation stack.

The stack creates:

- An internet-facing Application Load Balancer
- An ALB security group with HTTP access restricted to an approved public IP
- An EC2 security group allowing port 8080 only from the ALB
- A target group with health checks at `/health`
- An EC2 launch template using Amazon Linux 2023
- An Auto Scaling Group in private subnets

Auto Scaling configuration:

| Setting | Value |
|---|---|
| Minimum capacity | 1 |
| Desired capacity | 1 |
| Maximum capacity | 2 |
| Application port | 8080 |
| ALB listener | HTTP 80 |
| Health check | `/health` |

### 7.1 Identify your public IP

Determine your current public IPv4 address using a trusted public-IP service or your network configuration.

Set the allowed CIDR in PowerShell:

(Invoke-RestMethod -Uri "https://checkip.amazonaws.com").Trim()

```powershell
$AllowedCidr = "YOUR_PUBLIC_IP/32"
```

Replace `YOUR_PUBLIC_IP` with your actual public IPv4 address.

### 7.2 Deploy the application stack


with approval:
aws cloudformation deploy `
  --template-file cloudformation/provisioning/asg.yaml `
  --stack-name self-service-asg-test01 `
  --parameter-overrides AllowedCidr=$AllowedCidr `
  --no-execute-changeset `
  --tags Project=AWS-Self-Service Environment=Dev


without approval:
```powershell
aws cloudformation deploy `
  --template-file cloudformation/provisioning/asg.yaml `
  --stack-name self-service-asg-test01 `
  --parameter-overrides AllowedCidr=$AllowedCidr `
  --tags Project=AWS-Self-Service Environment=Dev
```

The deployment uses the network resources exported by Stack 1.

### 7.3 Verify the deployment

```powershell
aws cloudformation describe-stacks `
  --stack-name self-service-asg-test01 `
  --query "Stacks[0].StackStatus"
```

View stack outputs:

```powershell
aws cloudformation describe-stacks `
  --stack-name self-service-asg-test01 `
  --query "Stacks[0].Outputs"
```

look for:
"OutputKey": "ApplicationURL",
        "OutputValue": "http://self-service-asg-test01-alb-xx.eu-north-1.elb.amazonaws.com",
        "Description": "HTTP URL for the demo application"

Locate the Application Load Balancer DNS name and open:

```text
http://YOUR_ALB_DNS_NAME/health
http://self-service-asg-test01-alb-565139743.eu-north-1.elb.amazonaws.com/health
```
wait for few minutes (it taks time to publish public dns)

Expected response:

```json
{
  "status": "healthy"
}
```

This confirms that the request reaches the ALB, is forwarded to a healthy EC2 target, and receives a response from the application.

## 8. Operational Verification

List project stacks:

```powershell
aws cloudformation list-stacks `
  --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE `
  --query "StackSummaries[?starts_with(StackName, 'self-service-')].[StackName,StackStatus]"
```

Inspect stack resources:

```powershell
aws cloudformation list-stack-resources `
  --stack-name self-service-asg-test01
```

Inspect recent stack events:

```powershell
aws cloudformation describe-stack-events `
  --stack-name self-service-asg-test01 `
  --query "StackEvents[0:10].[Timestamp,LogicalResourceId,ResourceStatus,ResourceStatusReason]"
```

For troubleshooting, also inspect EC2 instance status, Auto Scaling activity, and ALB target-group health in the AWS Console.

## 9. Cleanup — Avoid Unnecessary AWS Charges

**Important:** The application stack creates billable resources, including an Application Load Balancer and EC2 instances.

Delete application stacks when they are no longer required.

### Delete Stack 3

```powershell
aws cloudformation delete-stack `
  --stack-name self-service-asg-test01

aws cloudformation wait stack-delete-complete `
  --stack-name self-service-asg-test01
```

### Delete Stack 2

```powershell
aws cloudformation delete-stack `
  --stack-name self-service-platform

aws cloudformation wait stack-delete-complete `
  --stack-name self-service-platform
```

### Delete Stack 1

```powershell
aws cloudformation delete-stack `
  --stack-name self-service-network

aws cloudformation wait stack-delete-complete `
  --stack-name self-service-network
```

Delete application stacks before deleting the network stack because they depend on its exported resources.

For normal development, it is possible to retain Stacks 1 and 2 while deleting only Stack 3 to reduce ongoing costs. Check for any remaining billable resources.

## 10. Current Implementation Status

| Component | Status |
|---|---|
| Dedicated VPC and networking | Completed and tested |
| API Gateway and Lambda health endpoint | Completed and tested |
| ALB and private EC2 Auto Scaling Group | Completed and tested |
| Application health endpoint | Completed and tested |
| Automated provisioning through Lambda | Not implemented |
| Authenticated provisioning API | Not implemented |
| CloudFormation stack status tracking | Not implemented |
| Developer self-service portal | Not implemented |

## 11. Planned Enhancements

1. Separate Lambda application code from the inline CloudFormation definition.
2. Introduce an authenticated provisioning API with input validation.
3. Add least-privilege IAM permissions for CloudFormation provisioning.
4. Make provisioning templates accessible to Lambda, potentially through S3.
5. Implement CloudFormation `CreateStack` and status tracking.
6. Add application stack deletion and error handling.
7. Build a developer-facing self-service portal.
8. Optionally introduce VPC peering with the separate AWS Application Infrastructure environment.

## 12. Security Considerations

- EC2 instances run in private subnets without direct public IP addresses.
- The ALB is public but restricts inbound HTTP traffic to an approved CIDR.
- Application instances accept port 8080 traffic only from the ALB security group.
- Lambda provisioning permissions have not yet been implemented.
- Do not expose an unauthenticated public endpoint capable of creating AWS resources.
- The current HTTP listener is suitable for a controlled development proof of concept; production use should introduce HTTPS and appropriate authentication and security controls.

## 13. Project Goal

The long-term goal is to provide developers with a self-service interface that can provision isolated AWS application environments without requiring direct access to infrastructure administration tools.

CloudFormation manages infrastructure lifecycle, API Gateway and Lambda provide the control plane, and each application environment is independently created, monitored, and deleted.