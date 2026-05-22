variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.20.0.0/16"
}

variable "subnet_1_cidr" {
  description = "CIDR block for the first public subnet"
  type        = string
  default     = "10.20.1.0/24"
}

variable "subnet_2_cidr" {
  description = "CIDR block for the second public subnet"
  type        = string
  default     = "10.20.2.0/24"
}

variable "ssh_cidr_blocks" {
  description = "CIDR blocks allowed to connect via SSH"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "tags" {
  description = "Common tags to apply to network resources"
  type        = map(string)
  default     = {}
}
