locals {
  instance_type = "t3.micro"
  environment   = "development"
}

resource "aws_security_group" "basic_ec2" {
  name_prefix = "aws-mini-platform-basic-ec2-"

  description = "Dedicated security group for the basic EC2 platform product."
  vpc_id      = data.aws_vpc.default.id

  /*
   * No ingress blocks:
   * The EC2 instance accepts no inbound network connections.
   */

  egress {
    description = "Allow outbound IPv4 traffic."

    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.instance_name}-sg"
    Environment = local.environment
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_instance" "basic_ec2" {
  ami           = data.aws_ssm_parameter.amazon_linux_2023_ami.value
  instance_type = local.instance_type

  subnet_id = data.aws_subnet.selected.id

  vpc_security_group_ids = [
    aws_security_group.basic_ec2.id
  ]

  /*
   * Default subnets are public and may normally assign public IPs.
   * This explicitly prevents a public IPv4 address.
   */
  associate_public_ip_address = false

  /*
   * No SSH key is configured because the instance has no inbound
   * access and is not intended for direct SSH connections.
   */
  key_name = null

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 8
    encrypted             = true
    delete_on_termination = true
  }

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  tags = {
    Name        = var.instance_name
    Environment = local.environment
  }
}