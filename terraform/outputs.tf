output "aws_region" {
  description = "AWS Region where infrastructure was provisioned"
  value       = var.aws_region
}

output "vpc_id" {
  description = "The ID of the provisioned VPC"
  value       = aws_vpc.main.id
}

output "cluster_name" {
  description = "The name of the Amazon EKS cluster"
  value       = aws_eks_cluster.main.name
}

output "cluster_endpoint" {
  description = "Endpoint URL for Amazon EKS Control Plane API"
  value       = aws_eks_cluster.main.endpoint
}

output "public_subnet_ids" {
  description = "List of public subnet IDs (used by ALB)"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "List of private subnet IDs (used by worker nodes)"
  value       = aws_subnet.private[*].id
}

output "ecr_repository_url" {
  description = "URL of the Amazon ECR repository for image push"
  value       = aws_ecr_repository.chatbot.repository_url
}

output "load_balancer_controller_role_arn" {
  description = "IAM Role ARN for AWS Load Balancer Controller (IRSA)"
  value       = aws_iam_role.load_balancer_controller.arn
}

output "configure_kubectl_command" {
  description = "Command to configure kubectl context locally"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${aws_eks_cluster.main.name}"
}
