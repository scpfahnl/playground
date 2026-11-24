resource "helm_release" "argocd" {
  name             = "argocd"
  repository       = "https://argoproj.github.io/argo-helm"
  chart            = "argo-cd"
  version          = "10.9.4"
  namespace        = "argocd"
  create_namespace = true

  values = [yamlencode({
    global = {
      nodeSelector = local.control_node_selector
      tolerations  = local.control_tolerations
    }
    configs = {
      params = {
        "server.insecure" = true
      }
      cm = {
        url = "https://argocd.${var.env}.${var.domain}"
      }
    }
    controller = {
      resources = {
        requests = { cpu = "100m", memory = "512Mi" }
        limits   = { memory = "1Gi" }
      }
    }
    repoServer = {
      resources = {
        requests = { cpu = "50m", memory = "256Mi" }
        limits   = { memory = "1Gi" }
      }
    }
    applicationSet = {
      resources = {
        requests = { cpu = "25m", memory = "128Mi" }
        limits   = { memory = "256Mi" }
      }
    }
    redis = {
      resources = {
        requests = { cpu = "25m", memory = "64Mi" }
        limits   = { memory = "256Mi" }
      }
    }
    redisSecretInit = {
      resources = {
        requests = { cpu = "10m", memory = "32Mi" }
        limits   = { memory = "64Mi" }
      }
    }
    dex = {
      resources = {
        requests = { cpu = "10m", memory = "64Mi" }
        limits   = { memory = "128Mi" }
      }
    }
    notifications = {
      resources = {
        requests = { cpu = "10m", memory = "64Mi" }
        limits   = { memory = "128Mi" }
      }
    }
    server = {
      resources = {
        requests = { cpu = "25m", memory = "128Mi" }
        limits   = { memory = "256Mi" }
      }
      ingress = {
        enabled          = true
        ingressClassName = "alb"
        hostname         = "argocd.${var.env}.${var.domain}"
        annotations = {
          "alb.ingress.kubernetes.io/scheme"           = "internet-facing"
          "alb.ingress.kubernetes.io/target-type"      = "ip"
          "alb.ingress.kubernetes.io/listen-ports"     = jsonencode([{ HTTP = 80 }, { HTTPS = 443 }])
          "alb.ingress.kubernetes.io/ssl-redirect"     = "443"
          "alb.ingress.kubernetes.io/healthcheck-path" = "/healthz"
        }
      }
    }
  })]

  set_wo = [
    {
      name  = "configs.secret.argocdServerAdminPassword"
      value = bcrypt(ephemeral.random_password.argocd_admin.result)
      type  = "string"
    }
  ]
  set_wo_revision = 1
  reuse_values    = true

  depends_on = [
    aws_eks_node_group.control,
    aws_eks_addon.coredns,
    aws_eks_access_policy_association.admin,
    aws_eks_access_policy_association.terraform_ci,
  ]
}

resource "helm_release" "root_app" {
  name       = "root-app"
  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argocd-apps"
  version    = "2.0.6"
  namespace  = helm_release.argocd.namespace

  values = [yamlencode({
    applications = {
      root-app = {
        namespace = helm_release.argocd.namespace
        project   = "default"
        source = {
          repoURL        = "https://github.com/STEFFENS-GITHUB/playground.git"
          targetRevision = "main"
          path           = "shared-infra/helm/root-app"
          helm = {
            valuesObject = {
              cluster = {
                name             = aws_eks_cluster.main.name
                env              = var.env
                region           = "us-east-1"
                vpcId            = module.vpc.vpc_id
                domain           = "${var.env}.${var.domain}"
                karpenterQueue   = module.karpenter.queue_name
                nodeRole         = module.karpenter.node_iam_role_name
                grafanaSecretArn = aws_secretsmanager_secret.grafana_admin.arn
              }
            }
          }
        }
        destination = {
          server    = "https://kubernetes.default.svc"
          namespace = helm_release.argocd.namespace
        }
        syncPolicy = {
          automated = {
            prune    = true
            selfHeal = true
          }
        }
      }
    }
  })]
}
