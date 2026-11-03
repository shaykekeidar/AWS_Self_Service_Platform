# AWS Self-Service Platform

**Version:** V1 — implemented, control-plane verified POC  
**Last verification:** November 3, 2026  
**AWS Region:** `eu-north-1`

A CloudFormation-based AWS self-service proof of concept (POC). A local browser portal authenticates users with Amazon Cognito (OAuth 2.0 Authorization Code + PKCE) and calls protected API Gateway endpoints backed by Lambda. Lambda can request creation of a fixed application stack comprising an internet-facing Application Load Balancer (ALB) and an EC2 Auto Scaling Group (ASG) in private subnets.

**Scope:** V1 is a fixed-template, fixed-stack-name lab—not a general-purpose multi-tenant provisioning service. Provisioning creates billable AWS resources. The application stack is normally deleted after testing; the network and platform stacks may remain deployed at low usage-based cost.

## 1. Architecture

The project has three **independent, non-nested** CloudFormation stacks:

| Stack | Source template | Responsibility |
|---|---|---|
| `self-service-network` | `cloudformation/network/network.yaml` | Dedicated VPC, public/private subnets, internet gateway, routing, and exports |
| `self-service-platform` | `cloudformation/platform/platform.yaml` | API Gateway HTTP API, Lambda, IAM roles, Cognito User Pool, app client, and domain |
| `self-service-asg-lab01` | `cloudformation/provisioning/asg.yaml` | ALB, security groups, target group, listener, EC2 launch template, and ASG |

The network stack exports identifiers consumed by the application template via `Fn::ImportValue`. The platform stack can remain deployed while the application stack is absent. The application stack is **created on demand** through Lambda's CloudFormation `CreateStack` call. A separate manual stack name, `self-service-asg-test01`, was used during earlier testing and is not the portal's fixed provisioning target.

### Control-plane flow

```text
Browser at http://localhost:8094/
  -> Cognito Managed Login (authorization code + PKCE S256)
  -> Browser receives access token
  -> API Gateway HTTP API (JWT authorizer on protected routes)
  -> Lambda (Python 3.13)
  -> CloudFormation DescribeStacks or CreateStack
  -> self-service-asg-lab01 (when provisioning is requested)
```

`GET /health` is public. `GET /stack` and `POST /provision` require a Cognito access token with the `openid` scope, validated by API Gateway's JWT authorizer. Lambda also checks that the API Gateway authorizer context is present; it relies on API Gateway for cryptographic JWT validation.

### Application data path

```text
Approved public IPv4 /32 -> internet-facing ALB (HTTP :80)
  -> target group (HTTP :8080, GET /health)
  -> EC2 instance(s) in private subnets
```

The ASG has minimum/desired/maximum capacity **1/1/2**. There is no CPU-based scaling policy in V1; the ASG maintains desired capacity and can replace unhealthy instances.

## 2. Network design

| Component | CIDR |
|---|---|
| VPC | `10.50.0.0/16` |
| Public subnet A | `10.50.1.0/24` |
| Public subnet B | `10.50.2.0/24` |
| Private subnet A | `10.50.11.0/24` |
| Private subnet B | `10.50.12.0/24` |

Public subnets have an internet-gateway route and host the ALB. Private subnets have no NAT Gateway and no default internet route. EC2 instances run an embedded Python HTTP application installed through EC2 User Data, without downloading dependencies at startup. The launch template requires IMDSv2. The ALB security group permits HTTP from the approved `/32` only; the EC2 security group permits port 8080 from the ALB security group only.

## 3. Repository structure

```text
cloudformation/
  network/network.yaml
  platform/platform.yaml
  platform/platform-packaged.yaml
  provisioning/asg.yaml
lambda/platform/app.py
frontend/index.html
docs/adr/
scripts/Get-SelfServiceHealth.ps1
README.md
```

`platform.yaml` is the **source template**. `platform-packaged.yaml` is a generated deployment template whose Lambda `Code` property references an S3 ZIP artifact. Do not hand-edit the packaged file as the primary source of changes.

## 4. Prerequisites and configuration

- AWS CLI v2 with valid credentials and deployment permissions for CloudFormation, S3, IAM, Lambda, API Gateway, Cognito, EC2, Elastic Load Balancing, and Auto Scaling.
- PowerShell (examples below), Python 3 for serving the frontend, and a modern browser supporting Web Crypto.
- Region `eu-north-1`; commands below explicitly set this region.
- An S3 artifact bucket named `self-service-artifacts-<account-id>-eu-north-1` containing `cloudformation/asg.yaml` and the packaged Lambda ZIP. Creating and maintaining the bucket and uploading the application template are prerequisites; this README does not automate bucket creation.
- A Cognito user created or invited by an administrator. The user pool is configured for admin-created users only.

From the repository root:

```powershell
aws sts get-caller-identity
aws cloudformation validate-template --region eu-north-1 --template-body file://cloudformation/network/network.yaml
aws cloudformation validate-template --region eu-north-1 --template-body file://cloudformation/platform/platform-packaged.yaml
aws cloudformation validate-template --region eu-north-1 --template-body file://cloudformation/provisioning/asg.yaml
```

CloudFormation validation checks template syntax/basic structure, not all runtime permissions or successful deployment.

## 5. Deploy the network stack

**Skip this step if `self-service-network` is already deployed and unchanged.**

```powershell
aws cloudformation deploy `
  --region eu-north-1 `
  --template-file cloudformation/network/network.yaml `
  --stack-name self-service-network `
  --tags Project=AWS-Self-Service Environment=Dev

aws cloudformation list-exports --region eu-north-1 `
  --query "Exports[?starts_with(Name, 'self-service-')]"
```

Expected exports: `self-service-vpc-id`, `self-service-public-subnet-a`, `self-service-public-subnet-b`, `self-service-private-subnet-a`, `self-service-private-subnet-b`.

## 6. Package and deploy the platform

**Skip deployment if the platform is already deployed and no code or template changes are intended.** Packaging uploads the local Lambda code to S3; deployment updates AWS resources and can incur charges.

Set the account-specific bucket name:

```powershell
$Region = 'eu-north-1'
$AccountId = (aws sts get-caller-identity --query Account --output text).Trim()
$Bucket = "self-service-artifacts-$AccountId-$Region"
```

Upload the provisioning template that Lambda will request. Keep its S3 key exactly `cloudformation/asg.yaml`, as referenced in the Lambda environment and IAM conditions:

```powershell
aws s3 cp cloudformation/provisioning/asg.yaml "s3://$Bucket/cloudformation/asg.yaml" --region $Region
```

Package the Lambda directory referenced by `platform.yaml`:

```powershell
aws cloudformation package `
  --region $Region `
  --template-file cloudformation/platform/platform.yaml `
  --s3-bucket $Bucket `
  --output-template-file cloudformation/platform/platform-packaged.yaml
```

Deploy the generated template. The source defines named IAM roles, so use `CAPABILITY_NAMED_IAM`:

```powershell
aws cloudformation deploy `
  --region $Region `
  --template-file cloudformation/platform/platform-packaged.yaml `
  --stack-name self-service-platform `
  --capabilities CAPABILITY_NAMED_IAM `
  --tags Project=AWS-Self-Service Environment=Dev
```

Retrieve configuration values:

```powershell
aws cloudformation describe-stacks `
  --region $Region `
  --stack-name self-service-platform `
  --query 'Stacks[0].Outputs' `
  --output table
```

Look for `ApiEndpoint`, `HealthEndpoint`, `PortalCognitoDomain`, `PortalAppClientId`, and `PortalUserPoolId`. These identifiers are not secrets; **never publish access tokens, authorization codes, passwords, or AWS credentials**.

## 7. Run the self-service portal

The frontend is a local static HTML page, not an S3/CloudFront website.

```powershell
cd frontend
python -m http.server 8094
```

Open `http://localhost:8094/`. Configure the API Gateway base URL, Cognito domain, and app client ID using the platform stack outputs. The frontend saves these **public configuration identifiers** in browser `localStorage`. It keeps the access token in page memory only; a page refresh requires another login.

1. Select **Check API health**; this calls unauthenticated `GET /health`.
2. Select **Login with Cognito**. The browser generates a PKCE verifier/challenge and OAuth state, redirects to Cognito Managed Login, validates the returned state, and exchanges the authorization code for tokens.
3. Select **Check ASG stack status**. This calls authenticated `GET /stack`. If the fixed application stack does not exist, the expected response is `{"status":"NOT_FOUND","stackName":"self-service-asg-lab01"}`.
4. Only when intentionally testing billable provisioning: enter your current public IPv4 address (without `/32`) and select **Provision ASG — lab01**. Confirm the browser prompt. Lambda validates the global IPv4 address, converts it to `/32`, and requests `CreateStack` with `t3.micro`.
5. A successful request returns HTTP **202** with `CREATE_REQUESTED`. This is **not** a guarantee of successful infrastructure creation. Use **Refresh stack status** to monitor CloudFormation. V1 does not auto-poll.

To discover the public IPv4 address from PowerShell:

```powershell
(Invoke-RestMethod -Uri 'https://checkip.amazonaws.com').Trim()
```

If the public IP changes, the existing ALB security-group rule does not update automatically. The frontend requires a fresh status check before provisioning and prevents repeat submission while a request is in progress. The backend returns HTTP 409 if the fixed stack already exists.

### API routes

| Method | Route | Authorization | Behavior |
|---|---|---|---|
| GET | `/health` | None | Reports API Gateway-to-Lambda health |
| GET | `/stack` | Cognito JWT (`openid` scope) | Returns current fixed stack status or `NOT_FOUND` |
| POST | `/provision` | Cognito JWT (`openid` scope) | Validates `{"publicIp":"x.x.x.x"}` and requests fixed stack creation |

There are no portal/API endpoints to update or delete application stacks in V1.

## 8. Application stack details and optional manual testing

The application template creates an ALB, security groups, listener, target group, launch template, and ASG. The EC2 User Data writes a Python HTTP server and a `systemd` service. Application endpoints are `/` and `/health`; ALB health checks expect HTTP 200 on `/health` at port 8080.

For a **separate, manual application test** (not the fixed portal target), choose a stack name such as `self-service-asg-test01`:

```powershell
$PublicIp = (Invoke-RestMethod -Uri 'https://checkip.amazonaws.com').Trim()
$AllowedCidr = "$PublicIp/32"

# Prepare a change set without executing it:
aws cloudformation deploy `
  --region eu-north-1 `
  --template-file cloudformation/provisioning/asg.yaml `
  --stack-name self-service-asg-test01 `
  --parameter-overrides AllowedCidr=$AllowedCidr `
  --no-execute-changeset `
  --tags Project=AWS-Self-Service Environment=Dev
```

**Warning:** Removing `--no-execute-changeset` permits creation of billable ALB/EC2 resources. Only do so with explicit intent. Manual testing is optional and separate from portal provisioning.

After successful deployment, inspect stack outputs for `ApplicationURL` and verify `http://<ALB-DNS>/health` from the approved public IP. Allow time for instance initialization and ALB target health checks. `CREATE_COMPLETE` alone does not prove the application is healthy.

## 9. Read-only operational verification

```powershell
aws cloudformation list-stacks `
  --region eu-north-1 `
  --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE CREATE_IN_PROGRESS UPDATE_IN_PROGRESS `
  --query "StackSummaries[?starts_with(StackName, 'self-service-')].[StackName,StackStatus]" `
  --output table

aws lambda get-function-configuration `
  --region eu-north-1 `
  --function-name self-service-platform-handler `
  --query '{Name:FunctionName,State:State,LastUpdateStatus:LastUpdateStatus,Runtime:Runtime,CodeSha256:CodeSha256}'

$ApiEndpoint = (aws cloudformation describe-stacks `
  --region eu-north-1 `
  --stack-name self-service-platform `
  --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue | [0]" `
  --output text).Trim()
Invoke-RestMethod -Uri "$ApiEndpoint/health"
```

For authenticated `GET /stack`, use the local portal. Do not paste bearer tokens into terminal logs or shared messages. For application stack diagnostics, inspect CloudFormation stack events, Auto Scaling activities, and ALB target-group health.

## 10. Cleanup and cost controls

**Billable resources:** An application stack creates an ALB and EC2 instances, and may incur associated network, storage, and other charges. Lambda, API Gateway, Cognito, S3, and related platform services can also incur charges depending on usage and free-tier eligibility. The network/platform stacks are **not guaranteed free**.

Delete application stacks after testing. The following commands are destructive; review the target stack name first:

```powershell
aws cloudformation delete-stack --region eu-north-1 --stack-name self-service-asg-lab01
aws cloudformation wait stack-delete-complete --region eu-north-1 --stack-name self-service-asg-lab01
```

If you created a separate `self-service-asg-test01` stack, delete it separately. To completely dismantle the lab, delete all application stacks first, then `self-service-platform`, then `self-service-network`. Network exports cannot be removed while still imported by an application stack. Check AWS billing and any residual resources after cleanup.

## 11. Security and V1 limitations

**Implemented guardrails:**

- Cognito Managed Login with OAuth 2.0 Authorization Code + PKCE (S256) and OAuth state validation.
- API Gateway JWT authorizer on provisioning and stack-status routes; access token requested with `openid email` scopes.
- Fixed stack name `self-service-asg-lab01`, fixed provisioning template S3 URL, fixed `t3.micro` instance type, and backend validation of the allowed global IPv4 `/32`.
- Separate Lambda and CloudFormation execution IAM roles; IAM conditions constrain the CloudFormation execution role ARN and provisioning template URL.
- Public ALB ingress restricted to the approved IPv4 `/32`; private EC2 instances accept traffic only from the ALB security group.
- EC2 IMDSv2 required. No NAT Gateway and no public EC2 IP addresses.
- Browser confirmation before provisioning; HTTP 409 for an existing stack.

**Known limitations / future hardening:**

- ALB listener uses **HTTP**, not HTTPS; suitable only for a controlled lab.
- Some CloudFormation execution role permissions use `Resource: '*'`; tighten IAM scope and review permissions for production.
- No automatic stack-status polling, app URL display in the portal, token refresh, or background session-expiration UI updates.
- No portal/API deletion, updates, template catalog, user-specific stack isolation, quotas, approval workflow, or FinOps estimates.
- CloudFormation `OnFailure=DELETE` may remove failed stacks before detailed troubleshooting; `CREATE_REQUESTED` is not proof of application readiness.
- No dynamic ASG scaling policy. No configured SSM instance profile or private connectivity for Session Manager.
- No formal production readiness, load testing, or multi-user authorization model.

## 12. Verification record — November 3, 2026

| Verification | Result |
|---|---|
| `self-service-network` | `CREATE_COMPLETE` |
| `self-service-platform` | `UPDATE_COMPLETE` |
| Deployed Lambda `self-service-platform-handler` | `Active`; last update `Successful`; Python 3.13 |
| API Gateway `GET /health` | Returned `healthy` and expected service/message |
| Cognito login + protected `GET /stack` | User reported successful end-to-end portal test |
| Packaged Lambda ZIP exists in S3 | Confirmed |
| Deployed Lambda `CodeSha256` matches referenced S3 ZIP | Confirmed exact match |
| Local `app.py` content matches packaged ZIP | **Not separately verified** |
| Live `POST /provision` and new application creation | **Not rerun in this final session**; application stacks intentionally absent |

The control plane is **verified**. Prior application deployment/ALB health testing is documented in the earlier README, but a new end-to-end provisioning run was deliberately not performed during this final verification to avoid billable resources.

## 13. V1 completion and roadmap

**V1 status:** Implementation complete and control-plane verified; README updated. V1 is considered a completed **proof of concept** with the explicit verification limitations above, not a production-ready platform.

Potential future versions: automatic status polling and improved UX; portal-managed deletion and lifecycle operations; stronger IAM restrictions; a reusable template catalog (EC2, ECS, EKS, RDS); FinOps cost estimation; and expanded operational observability.

The long-term objective remains developer self-service infrastructure provisioning without giving application users direct infrastructure administration permissions.