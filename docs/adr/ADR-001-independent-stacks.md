# ADR-001: Independent CloudFormation Stacks

**Status:** Accepted  
**Project:** AWS Self-Service Platform

## Context

The platform requires networking infrastructure, a centralized provisioning API, and dynamically created application environments.

These components have different lifecycles and should be managed independently.

## Decision

Use three independent CloudFormation stacks:

1. `self-service-network` — VPC, public/private subnets, Internet Gateway, and routing.
2. `self-service-platform` — API Gateway, Lambda, and IAM execution roles.
3. `self-service-asg-<request-id>` — ALB, Target Group, Launch Template, Security Groups, and EC2 Auto Scaling Group.

Each stack will use its own CloudFormation template.

The provisioning Lambda will create and delete application stacks according to authorized developer requests.

Networking resources will be shared through CloudFormation Outputs and Exports.

## Alternatives Considered

- **Single CloudFormation stack:** Simpler initially, but combines resources with different lifecycles.
- **Nested stacks:** Support modularity but introduce parent-stack orchestration and dependencies.

## Consequences

**Advantages**
- Independent deployment and updates.
- Application environments can be created and deleted without deleting the network.
- Clear separation of responsibilities.
- Reusable foundational infrastructure.

**Trade-offs**
- Stack dependencies must be managed.
- Exported values cannot be changed or removed while imported by other stacks.
- Stack creation and deletion order must be controlled.

## Implementation

Templates:
- `cloudformation/network/network.yaml`
- `cloudformation/platform/platform.yaml`
- `cloudformation/provisioning/asg.yaml`