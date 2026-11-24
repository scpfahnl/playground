# Playground

A monorepo for a reusable infra platform and the apps that run on it.

- `infra/terraform/` builds the AWS environment: VPC, EKS, Aurora, Valkey, SQS and ArgoCD.
- `infra/helm/` holds the charts ArgoCD deploys. `root-app` is the app-of-apps, `karpenter-nodepool` defines the worker nodes, and each app has its own chart alongside them.
- `applications/` holds the apps. Each app lives in `applications/<app>/` with one directory per service and its own README.

## Applications

- `applications/journal-app/` is a personal journalling service with an API and an email-verification worker. Chart: `infra/helm/journal-app/`.

## Deploying

Infrastructure is applied by running `.github/workflows/terraform-deploy.yml` manually with an `environment` input, which selects `infra/terraform/variables/<environment>.tfvars` and `.tfbackend`.

Terraform installs ArgoCD and the `root-app` Application. From then on ArgoCD keeps the cluster in sync with `infra/helm/` on `main`.

App images are built by each app's own workflows. See the app's README.
