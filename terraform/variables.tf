variable "aws_region" {
  description = "The AWS region to deploy all resources into"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment name"
  type        = string
  default     = "poc"
}

variable "cluster_name" {
  description = "The name of the Amazon EKS cluster"
  type        = string
  default     = "streamlit-chatbot-eks"
}

variable "vpc_cidr" {
  description = "Base CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for the two public subnets (across two AZs)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for the two private subnets (across two AZs)"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.20.0/24"]
}

variable "node_instance_types" {
  description = "EC2 instance types for the private EKS managed node group"
  type        = list(string)
  default     = ["t3.medium"]
}

variable "desired_capacity" {
  description = "Desired number of worker nodes in the private node group"
  type        = number
  default     = 2
}

variable "min_capacity" {
  description = "Minimum number of worker nodes in the private node group"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Maximum number of worker nodes in the private node group"
  type        = number
  default     = 3
}

variable "ecr_repository_name" {
  description = "Name of the Amazon ECR repository for the chatbot container image"
  type        = string
  default     = "eks-streamlit-chatbot"
}
