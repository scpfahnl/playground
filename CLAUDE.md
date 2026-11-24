## Architecture

This is a monorepo for a reusable infra platform plus the apps that run on it. Each app lives under `applications/<app>/` with one directory per service.

Platform:
- `shared-infra/terraform/bootstrap/` — one-time account setup (delegated Route 53 zone, GitHub OIDC provider, `terraform-ci` role). Applied locally, not by CI. Separate state key `bootstrap/terraform.tfstate`.
- `shared-infra/terraform/` — main environment (VPC, EKS, ArgoCD, etc.), applied by .github/workflows/terraform.yml
- `shared-infra/helm/` — charts ArgoCD deploys

Journal app:
- `applications/journal-app/api/` — python FastAPI backend, built into a docker image and pushed to dockerhub (CI: .github/workflows/api-image-build.yml)
- `applications/journal-app/compose.yaml` — local stack and CI test dependencies, reads `applications/journal-app/.env`
- `applications/journal-app/worker/` — worker service that reads email-verification jobs from an SQS queue (CI: .github/workflows/worker-image-build.yml)
- `applications/journal-app/cli/` — click-based command-line client for the API (installable via applications/journal-app/cli/pyproject.toml)

## Important Commands

## Important Caveats

## Important Past Mistakes to Avoid

Be concise with answers, dont drag on.
Explain what you are doing before proposing changes.
Use the edit tool for file changes.