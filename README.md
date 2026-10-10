# 🤖 AWS EKS Streamlit Q&A Chatbot (Private Worker Nodes & ALB)

[![AWS EKS](https://img.shields.io/badge/AWS-EKS%20v1.30-orange?logo=amazon-aws)](https://aws.amazon.com/eks/)
[![Terraform](https://img.shields.io/badge/IaC-Terraform%201.5%2B-blueviolet?logo=terraform)](https://www.terraform.io/)
[![Docker](https://img.shields.io/badge/Container-Docker-blue?logo=docker)](https://www.docker.com/)
[![Kubernetes](https://img.shields.io/badge/Orchestration-Kubernetes-326CE5?logo=kubernetes)](https://kubernetes.io/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit%201.36-FF4B4B?logo=streamlit)](https://streamlit.io/)
[![Groq](https://img.shields.io/badge/LLM%20Engine-Groq%20Cloud-f55036)](https://groq.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A production-ready Proof of Concept (POC) demonstrating how to deploy an interactive **Streamlit Q&A Chatbot** powered by **Groq Cloud AI (`gpt-120b`, `llama-3.3-70b`, `deepseek-r1`)** on **Amazon EKS** using **private EC2 worker nodes** (zero public IPv4 addresses) and expose it publicly via an **AWS Application Load Balancer (ALB)** with native health checks.

---

## 📑 Table of Contents

- [⚡ Quick Start (TL;DR)](#-quick-start-tldr)
- [🏗️ Architecture & Traffic Flow](#️-architecture--traffic-flow)
- [✨ Key Features](#-key-features)
- [📁 Repository Structure](#-repository-structure)
- [🧰 Prerequisites & Tools Check](#-prerequisites--tools-check)
- [💻 Local Development Guide](#-local-development-guide)
- [🚀 Cloud Deployment Workflow](#-cloud-deployment-workflow)
  - [Step 1: Terraform Infrastructure](#step-1-provision-infrastructure-with-terraform)
  - [Step 2: Kubectl Context & Node Verification](#step-2-configure-kubectl--verify-private-nodes)
  - [Step 3: AWS Load Balancer Controller (Helm)](#step-3-install-aws-load-balancer-controller)
  - [Step 4: Build & Push Docker Image to ECR](#step-4-build-tag--push-docker-image-to-ecr)
  - [Step 5: Deploy Kubernetes Manifests](#step-5-deploy-chatbot-to-kubernetes)
  - [Step 6: Access Chatbot via ALB](#step-6-access-the-chatbot)
- [⚡ Groq AI & Model Configuration](#-groq-ai--model-configuration)
- [🔍 Troubleshooting & Runbook](#-troubleshooting--runbook)
- [🧹 Cost Optimization & Destruction Order](#-cost-optimization--destruction-order)

---

## ⚡ Quick Start (TL;DR)

Want to get it running immediately?

```bash
# 1. Clone & Enter repo
cd eks-streamlit-chatbot-poc/terraform

# 2. Provision AWS Infrastructure
terraform init && terraform apply -auto-approve

# 3. Connect kubectl
aws eks update-kubeconfig --region $(terraform output -raw aws_region) --name $(terraform output -raw cluster_name)

# 4. Install ALB Controller via Helm
helm repo add eks https://aws.github.io/eks-charts && helm repo update eks
helm install aws-load-balancer-controller eks/aws-load-balancer-controller -n kube-system \
  --set clusterName=$(terraform output -raw cluster_name) \
  --set serviceAccount.create=true \
  --set serviceAccount.name=aws-load-balancer-controller \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=$(terraform output -raw load_balancer_controller_role_arn) \
  --set region=$(terraform output -raw aws_region) \
  --set vpcId=$(terraform output -raw vpc_id)

# 5. Build, Push & Apply
cd ../app && docker build -t streamlit-chatbot:latest .
# Authenticate & push to ECR, then:
cd ../k8s && kubectl apply -f deployment.yaml -f service.yaml -f ingress.yaml
```

---

## 🏗️ Architecture & Traffic Flow

```
                      [ User Browser ]
                             │
                             ▼  (HTTP Port 80)
                       [ Internet ]
                             │
                             ▼
                  [ Internet Gateway (IGW) ]
                             │
                             ▼
            [ Public Application Load Balancer ]
          (Provisioned across 2 Public Subnets in 2 AZs)
                             │
                             ▼  (Direct Pod IP Target Routing)
                   [ Kubernetes Ingress ]
                             │
                             ▼
                   [ ClusterIP Service ]
                       (Port: 8501)
                             │
                             ▼
                 [ Streamlit Chatbot Pods ]
            (Port 8501 | Health: /_stcore/health)
                             │
                             ▼
               [ Private EKS Worker Nodes ]
         (Zero Public IP | Hosted in 2 Private Subnets)
                             │
                             ▼  (Outbound HTTPS Port 443)
                   [ Single NAT Gateway ]
                   (In Public Subnet AZ-1)
                             │
                             ▼
            [ Groq Cloud API & Amazon ECR Registry ]
```

---

## ✨ Key Features

- **Zero Public IP on Compute:** Worker nodes run strictly in private subnets, shielding EC2 instances from direct Internet attacks or port-scanning.
- **50% NAT Cost Reduction:** Uses 1 NAT Gateway instead of multi-AZ NAT Gateways, saving ~$32/month for non-production environments.
- **Direct IP Mode (ALB):** AWS Load Balancer Controller routes traffic directly to private Pod IPs, eliminating inefficient `NodePort` hops.
- **AI Streaming UI:** Integrated with Groq Cloud for ultra-fast token streaming supporting:
  - `gpt-120b` (Custom selectable model)
  - `llama-3.3-70b-versatile` (Flagship)
  - `deepseek-r1-distill-llama-70b` (Reasoning)
  - `llama-3.1-8b-instant` (Speed)
  - `mixtral-8x7b-32768` (MoE)
- **Zero-Downtime Rolling Updates:** Kubernetes deployment configured with `maxSurge: 1`, `maxUnavailable: 0`, and native Streamlit health probes (`/_stcore/health`).

---

## 📁 Repository Structure

```
eks-streamlit-chatbot-poc/
├── app/
│   ├── .env.example              # Environment variables template
│   ├── Dockerfile                # Multi-stage lightweight Python 3.11 container
│   ├── main.py                   # Streamlit app with Groq SDK & streaming chat UI
│   └── requirements.txt          # Dependencies: streamlit, python-dotenv, groq
├── terraform/
│   ├── ecr.tf                    # Amazon ECR container repository with scan-on-push
│   ├── eks.tf                    # Amazon EKS v1.30, private managed node group, add-ons
│   ├── iam.tf                    # IRSA roles (Cluster, Nodes, Load Balancer Controller)
│   ├── main.tf                   # Availability zones & AWS caller identity
│   ├── networking.tf             # VPC, 2 public subnets, 2 private subnets, IGW, 1 NAT GW
│   ├── outputs.tf                # Cluster name, ECR URL, role ARNs, and helpers
│   ├── providers.tf              # AWS provider configuration
│   ├── terraform.tfvars.example  # Example variable overrides
│   ├── variables.tf              # Configurable variables with defaults
│   └── versions.tf               # Terraform and provider version constraints
├── k8s/
│   ├── deployment.yaml           # Deployment with 2 replicas, probes, resources & secrets
│   ├── ingress.yaml              # Internet-facing ALB ingress with IP target type
│   └── service.yaml              # Internal ClusterIP service on port 8501
├── .env                          # Local development environment (gitignored)
├── .gitignore                    # Protects .env, certificates, and terraform state
└── README.md                     # Developer documentation
```

---

## 🧰 Prerequisites & Tools Check

Ensure you have the following installed on your developer machine:

| Tool | Recommended Version | Check Command |
| :--- | :--- | :--- |
| **AWS CLI** | `2.15+` | `aws --version` |
| **Terraform** | `1.5.0+` | `terraform -version` |
| **Docker** | `24+` | `docker --version` |
| **kubectl** | `1.28+` | `kubectl version --client` |
| **Helm** | `3.12+` | `helm version` |

### AWS CLI Authentication Check
Ensure you are logged into an IAM user with appropriate permissions (VPC, EKS, EC2, IAM, ECR):

```bash
aws sts get-caller-identity
```

---

## 💻 Local Development Guide

You can run and test the Streamlit chatbot locally on your laptop in seconds before touching cloud infrastructure.

### Option 1: Running with Python Virtualenv

```bash
cd app

# 1. Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\Activate.ps1
# On macOS/Linux:
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) Set Groq API Key
export GROQ_API_KEY="gsk_your_groq_api_key_here"  # Linux/macOS
$env:GROQ_API_KEY="gsk_your_groq_api_key_here"   # Windows PowerShell

# 4. Run Streamlit
streamlit run main.py
```
*Open [http://localhost:8501](http://localhost:8501) in your browser.*

### Option 2: Running with Local Docker Container

```bash
cd app
docker build -t streamlit-chatbot:local .
docker run -p 8501:8501 -e GROQ_API_KEY="gsk_your_key" streamlit-chatbot:local
```

---

## 🚀 Cloud Deployment Workflow

Follow these steps sequentially to deploy the POC to AWS.

### Step 1: Provision Infrastructure with Terraform

```bash
cd terraform
terraform init
terraform plan
terraform apply -auto-approve
```

#### Export Useful Terraform Variables:
<details open>
<summary><b>Linux / macOS (Bash)</b></summary>

```bash
export AWS_REGION=$(terraform output -raw aws_region)
export CLUSTER_NAME=$(terraform output -raw cluster_name)
export ECR_REPO_URL=$(terraform output -raw ecr_repository_url)
export ALB_ROLE_ARN=$(terraform output -raw load_balancer_controller_role_arn)
export VPC_ID=$(terraform output -raw vpc_id)
```
</details>

<details>
<summary><b>Windows (PowerShell)</b></summary>

```powershell
$env:AWS_REGION = (terraform output -raw aws_region)
$env:CLUSTER_NAME = (terraform output -raw cluster_name)
$env:ECR_REPO_URL = (terraform output -raw ecr_repository_url)
$env:ALB_ROLE_ARN = (terraform output -raw load_balancer_controller_role_arn)
$env:VPC_ID = (terraform output -raw vpc_id)
```
</details>

---

### Step 2: Configure kubectl & Verify Private Nodes

```bash
# Update local kubeconfig context
aws eks update-kubeconfig --region $AWS_REGION --name $CLUSTER_NAME

# Check worker nodes
kubectl get nodes -o wide
```

> [!NOTE]
> Verify that the `EXTERNAL-IP` column shows `<none>`. This confirms that all EC2 instances are isolated inside private subnets without public IPv4 exposure.

---

### Step 3: Install AWS Load Balancer Controller

Install the controller using Helm with IAM Roles for Service Accounts (IRSA):

```bash
helm repo add eks https://aws.github.io/eks-charts
helm repo update eks

helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=$CLUSTER_NAME \
  --set serviceAccount.create=true \
  --set serviceAccount.name=aws-load-balancer-controller \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=$ALB_ROLE_ARN \
  --set region=$AWS_REGION \
  --set vpcId=$VPC_ID
```

Verify deployment:
```bash
kubectl get deployment -n kube-system aws-load-balancer-controller
```

---

### Step 4: Build, Tag & Push Docker Image to ECR

```bash
cd ../app

# 1. Log in to Amazon ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPO_URL

# 2. Build image
docker build -t streamlit-chatbot:latest .

# 3. Tag & Push
docker tag streamlit-chatbot:latest $ECR_REPO_URL:latest
docker push $ECR_REPO_URL:latest
```

---

### Step 5: Deploy Chatbot to Kubernetes

```bash
cd ../k8s

# 1. Replace placeholder in deployment.yaml
# Linux/macOS:
sed -i "s|REPLACE_WITH_ECR_IMAGE_URL|$ECR_REPO_URL:latest|g" deployment.yaml
# Windows PowerShell:
# (Get-Content deployment.yaml) -replace 'REPLACE_WITH_ECR_IMAGE_URL', "$($env:ECR_REPO_URL):latest" | Set-Content deployment.yaml

# 2. (Optional) Create Kubernetes Secret for Groq API Key:
kubectl create secret generic chatbot-secrets --from-literal=groq-api-key="gsk_your_groq_api_key_here"

# 3. Apply manifests
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml
```

Verify Pods:
```bash
kubectl get pods -l app=streamlit-chatbot -o wide
```

---

### Step 6: Access the Chatbot

Retrieve the public ALB DNS hostname:

```bash
kubectl get ingress streamlit-chatbot-ingress
```

*Example Output:*
```text
NAME                        CLASS   HOSTS   ADDRESS                                                                 PORTS   AGE
streamlit-chatbot-ingress   alb     *       k8s-default-streamli-1a2b3c4d-123456789.us-east-1.elb.amazonaws.com    80      2m
```

Copy the `ADDRESS` and open in your browser:
```text
http://k8s-default-streamli-1a2b3c4d-123456789.us-east-1.elb.amazonaws.com
```

---

## ⚡ Groq AI & Model Configuration

The application includes native support for Groq's high-speed inference engine.

### Supported Models (Sidebar Selector)
- **`gpt-120b`**: Directly selectable option in the UI dropdown.
- **`llama-3.3-70b-versatile`**: Recommended general-purpose model.
- **`deepseek-r1-distill-llama-70b`**: High-performance reasoning model.
- **`llama-3.1-8b-instant`**: Sub-100ms ultra-low latency model.
- **`mixtral-8x7b-32768`**: Large context window (32k tokens).
- **`Custom Model`**: Input field to specify any future Groq model ID.

### Getting a Free Groq API Key
1. Visit [console.groq.com/keys](https://console.groq.com/keys).
2. Create an API key (`gsk_...`).
3. Enter it in the chatbot sidebar input box, or set it via `.env` / Kubernetes Secret.

---

## 🔍 Troubleshooting & Runbook

| Problem | Root Cause | Diagnosis & Fix |
| :--- | :--- | :--- |
| **`ImagePullBackOff`** | Node cannot reach ECR or lacks IAM permissions | Run `kubectl describe pod <name>`. Check that NAT Gateway is deployed and the Node role has `AmazonEC2ContainerRegistryReadOnly`. |
| **ALB Not Created** | Subnet discovery tags missing or ALB Controller error | Run `kubectl logs -n kube-system deployment/aws-load-balancer-controller`. Verify public subnets have tag `kubernetes.io/role/elb = 1`. |
| **ALB Targets Unhealthy** | Streamlit health path mismatch | Streamlit health endpoint is `/_stcore/health` on port `8501`. Verify annotation `alb.ingress.kubernetes.io/healthcheck-path: /_stcore/health`. |
| **Pods stuck in `Pending`** | Insufficient CPU/Memory or Nodes not ready | Run `kubectl get nodes` and `kubectl describe pod <name>`. Adjust pod CPU requests if using small instance sizes. |
| **Unauthorized `kubectl`** | AWS CLI IAM identity mismatch | Run `aws sts get-caller-identity`. The IAM role that ran Terraform must be the same one calling kubectl. |

---

## 🧹 Cost Optimization & Destruction Order

> [!CAUTION]
> Resources like EKS Control Plane ($0.10/hr), NAT Gateway ($0.045/hr + data fees), and ALB incur hourly charges. Always clean up when testing is finished.

Execute cleanup in this **exact order** to prevent orphan load balancers and dependency lock errors:

```bash
# 1. Delete Ingress (Deletes AWS ALB automatically)
cd k8s
kubectl delete -f ingress.yaml
kubectl delete -f service.yaml
kubectl delete -f deployment.yaml

# Wait 90 seconds for ALB to finish deletion in AWS:
sleep 90

# 2. Uninstall ALB Controller
helm uninstall aws-load-balancer-controller -n kube-system

# 3. Destroy Terraform Infrastructure
cd ../terraform
terraform destroy -auto-approve

# 4. Verify no remaining billable resources
aws elbv2 describe-load-balancers --region us-east-1
aws eks list-clusters --region us-east-1
```

---

## 📚 Official Documentation & Source References

All configurations, annotations, IAM policies, and architecture standards in this repository are strictly derived from official documentation and upstream repositories:

| Technology | Resource Type | Official URL & Source Repository |
| :--- | :--- | :--- |
| **AWS EKS** | Official AWS User Guide | [Amazon EKS User Guide](https://docs.aws.amazon.com/eks/latest/userguide/) |
| **AWS EKS IAM Roles** | Cluster & Node Policies | [AWS Service IAM Role Docs](https://docs.aws.amazon.com/eks/latest/userguide/service_IAM_role.html) |
| **AWS Load Balancer Controller** | GitHub Source Repository | [kubernetes-sigs/aws-load-balancer-controller](https://github.com/kubernetes-sigs/aws-load-balancer-controller) |
| **ALB Controller IAM Policy** | Official Upstream Policy | [Official `iam_policy.json`](https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/main/docs/install/iam_policy.json) |
| **ALB Ingress Annotations** | Official Ingress Specification | [Kubernetes-SIGs ALB Ingress Annotations](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/ingress/annotations/) |
| **ALB Subnet Discovery Tags** | Official Tagging Guide | [Kubernetes-SIGs Subnet Discovery Guide](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/deploy/subnet_discovery/) |
| **AWS EKS Helm Charts** | Official Helm Repository | [AWS EKS Charts Repository](https://aws.github.io/eks-charts/) |
| **Streamlit Framework** | Healthcheck & Monitoring | [Streamlit Monitoring & Healthcheck Docs](https://docs.streamlit.io/deploy/concepts/administration/monitoring#healthcheck) |
| **Streamlit Chat API** | UI Reference | [Streamlit Chat Elements Guide](https://docs.streamlit.io/develop/api-reference/chat) |
| **Groq Cloud AI** | Official API Reference | [Groq Cloud Documentation](https://console.groq.com/docs/quickstart) |
| **Groq Python SDK** | GitHub Source Repository | [groq/groq-python GitHub](https://github.com/groq/groq-python) |
| **Terraform AWS Provider** | HashiCorp Registry | [HashiCorp AWS Provider Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs) |
| **Kubernetes API** | Ingress, Service, Deployment | [Kubernetes Networking & Workloads Docs](https://kubernetes.io/docs/concepts/services-networking/ingress/) |

---

## 📄 License
This project is licensed under the MIT License - feel free to adapt it for your team or organization!
