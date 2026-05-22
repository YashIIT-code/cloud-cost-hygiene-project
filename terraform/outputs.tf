output "vpc_id" {
  description = "The ID of the VPC"
  value       = module.network.vpc_id
}

output "instance_1_id" {
  description = "The ID of the first EC2 instance"
  value       = aws_instance.app_1.id
}

output "instance_2_id" {
  description = "The ID of the second EC2 instance"
  value       = aws_instance.app_2.id
}

output "s3_bucket_name" {
  description = "The name of the S3 bucket"
  value       = aws_s3_bucket.artifacts.id
}
