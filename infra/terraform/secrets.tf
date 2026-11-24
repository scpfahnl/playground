ephemeral "random_password" "argocd_admin" {
  length  = 32
  special = false
}

resource "aws_secretsmanager_secret" "argocd_admin" {
  name                    = "${var.env}/playground/argocd-admin-password"
  recovery_window_in_days = 0

  tags = {
    Environment = var.env
  }
}

resource "aws_secretsmanager_secret_version" "argocd_admin" {
  secret_id                = aws_secretsmanager_secret.argocd_admin.id
  secret_string_wo         = ephemeral.random_password.argocd_admin.result
  secret_string_wo_version = 1
}

ephemeral "random_password" "grafana_admin" {
  length  = 32
  special = false
}

resource "aws_secretsmanager_secret" "grafana_admin" {
  name                    = "${var.env}/playground/grafana-admin"
  recovery_window_in_days = 0

  tags = {
    Environment = var.env
  }
}

resource "aws_secretsmanager_secret_version" "grafana_admin" {
  secret_id = aws_secretsmanager_secret.grafana_admin.id
  secret_string_wo = jsonencode({
    "admin-user"     = "admin"
    "admin-password" = ephemeral.random_password.grafana_admin.result
  })
  secret_string_wo_version = 1
}
