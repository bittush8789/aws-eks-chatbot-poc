# Discover available Availability Zones in the selected AWS region
data "aws_availability_zones" "available" {
  state = "available"
}

# Fetch current AWS account details
data "aws_caller_identity" "current" {}
