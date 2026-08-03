output "instance_id" {
  description = "ID of the EC2 instance created by the platform product."
  value       = aws_instance.basic_ec2.id
}

output "instance_name" {
  description = "Name assigned to the EC2 instance."
  value       = var.instance_name
}

output "instance_state" {
  description = "Current EC2 instance state."
  value       = aws_instance.basic_ec2.instance_state
}

output "private_ip" {
  description = "Private IPv4 address of the EC2 instance."
  value       = aws_instance.basic_ec2.private_ip
}

output "public_ip" {
  description = "Public IPv4 address; expected to be empty."
  value       = aws_instance.basic_ec2.public_ip
}

output "vpc_id" {
  description = "Default VPC used by the product."
  value       = data.aws_vpc.default.id
}

output "subnet_id" {
  description = "Default subnet selected by the product."
  value       = data.aws_subnet.selected.id
}

output "security_group_id" {
  description = "Dedicated security group created for the EC2 product."
  value       = aws_security_group.basic_ec2.id
}

output "ami_id" {
  description = "Amazon Linux 2023 AMI selected through Parameter Store."
  value       = data.aws_ssm_parameter.amazon_linux_2023_ami.value
}