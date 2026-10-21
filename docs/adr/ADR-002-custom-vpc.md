# ADR-002: Dedicated Custom VPC

**Status:** Accepted  
**Project:** AWS Self-Service Platform

## Context

AWS provides a Default VPC, currently identified in the development account with CIDR `172.31.0.0/16`.

The platform requires public subnets for the Application Load Balancer and private subnets for EC2 instances.

The network should also be independently managed using CloudFormation.

## Decision

Create a dedicated custom VPC using the `self-service-network` CloudFormation stack.

Proposed configuration:

- VPC CIDR: `10.50.0.0/16`
- Two public subnets across two Availability Zones.
- Two private subnets across two Availability Zones.
- Internet Gateway for public subnet routing.
- No NAT Gateway in the initial implementation.
- No public IPv4 addresses on application EC2 instances.

The proposed CIDR must be checked against other existing and planned VPCs before deployment.

## Alternatives Considered

**Default VPC**

Advantages:
- Already available.
- Less initial configuration.
- Suitable for simple experiments.

Disadvantages:
- Outside the project's CloudFormation network lifecycle.
- May be shared with unrelated resources.
- Less control over the initial network design.

## Consequences

**Advantages**
- Complete network ownership through CloudFormation.
- Reproducible infrastructure.
- Explicit control over subnet layout and routing.
- Independent lifecycle from the existing ECS Terraform project.
- Preparation for possible future VPC Peering.

**Trade-offs**
- Additional CloudFormation configuration.
- Network resources must be deployed before dependent stacks.
- Private EC2 instances have no internet egress without additional connectivity.
- Future connectivity between VPCs requires non-overlapping CIDRs.

## Implementation

Template:
`cloudformation/network/network.yaml`

Stack:
`self-service-network`