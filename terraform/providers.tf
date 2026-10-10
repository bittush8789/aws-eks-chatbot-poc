provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = var.environment
      Project     = "eks-streamlit-chatbot-poc"
      ManagedBy   = "Terraform"
    }
  }
}
