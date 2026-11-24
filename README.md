# Playground

`shared-infra/` is the shared platform: Terraform for AWS (`bootstrap/` for one-time account setup) and the ArgoCD root-app that deploys everything.
`applications/<app>/` holds each app, with a directory per service, a `compose.yaml` for local dev, and its own `infra/` for deployment.
Adding an app means adding its directory and an Application in `shared-infra/helm/root-app`.
