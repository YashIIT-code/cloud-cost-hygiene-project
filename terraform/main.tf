module "network" {
  source          = "./modules/network"
  ssh_cidr_blocks = var.ssh_allowed_cidrs
  tags            = var.common_tags
}

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

resource "aws_instance" "app_1" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t3.micro"
  subnet_id              = module.network.public_subnet_1_id
  vpc_security_group_ids = [module.network.security_group_id]

  tags = merge(var.common_tags, { Name = "app-instance-1" })
}

resource "aws_instance" "app_2" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t3.micro"
  subnet_id              = module.network.public_subnet_2_id
  vpc_security_group_ids = [module.network.security_group_id]

  # Deliberately missing some tags to trigger the cost janitor's tag check
  tags = {
    Name        = "app-instance-2"
    Environment = "Dev"
  }
}

resource "aws_s3_bucket" "artifacts" {
  bucket = "devops-internship-artifacts-bucket"
  tags   = merge(var.common_tags, { Name = "artifacts-bucket", Protected = "true" })
}

resource "aws_s3_bucket_versioning" "artifacts_versioning" {
  bucket = aws_s3_bucket.artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "artifacts_lifecycle" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    id     = "expire-noncurrent"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# Create an unattached EBS volume to be caught by the Cost Janitor
resource "aws_ebs_volume" "unattached_volume" {
  availability_zone = "us-east-1a"
  size              = 10
  tags              = merge(var.common_tags, { Name = "unattached-data-volume" })
}
