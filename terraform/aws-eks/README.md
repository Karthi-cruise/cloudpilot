# Optional Production Deployment on AWS EKS

This module provides the complete production Infrastructure as Code to provision CloudPilot on AWS Elastic Kubernetes Service (EKS).

## Architecture on AWS
- Multi-AZ VPC across 3 Availability Zones with private/public subnets and NAT Gateways.
- Managed EKS cluster with Kubernetes 1.31.
- EKS Managed Node Group with autoscaling from 2 to 6 worker nodes.
- Integrated IAM roles for Service Accounts (IRSA).

## Deployment Commands
```bash
cd terraform/aws-eks
terraform init
terraform plan
terraform apply

# Configure local kubectl to point to AWS EKS
aws eks --region us-east-1 update-kubeconfig --name cloudpilot-eks

# Deploy CloudPilot using Helm
helm upgrade --install cloudpilot ../../helm/cloudpilot --namespace cloudpilot --create-namespace
```
