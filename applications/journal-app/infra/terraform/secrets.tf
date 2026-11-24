ephemeral "random_password" "api_jwt_signing_key" {
  length  = 64
  special = false
}

resource "aws_secretsmanager_secret" "api_jwt_signing_key" {
  name                    = "${var.env}/journal/api-jwt-signing-key"
  recovery_window_in_days = 0

  tags = {
    Environment = var.env
  }
}

resource "aws_secretsmanager_secret_version" "api_jwt_signing_key" {
  secret_id                = aws_secretsmanager_secret.api_jwt_signing_key.id
  secret_string_wo         = ephemeral.random_password.api_jwt_signing_key.result
  secret_string_wo_version = 1
}

ephemeral "random_password" "db_master" {
  length  = 32
  special = false
}

resource "aws_secretsmanager_secret" "db_master" {
  name                    = "${var.env}/journal/db-master"
  recovery_window_in_days = 0

  tags = {
    Environment = var.env
  }
}

resource "aws_secretsmanager_secret_version" "db_master" {
  secret_id = aws_secretsmanager_secret.db_master.id
  secret_string_wo = jsonencode({
    username = aws_rds_cluster.aurora.master_username
    password = ephemeral.random_password.db_master.result
  })
  secret_string_wo_version = 1
}

resource "aws_secretsmanager_secret" "config" {
  name                    = "${var.env}/journal/config"
  recovery_window_in_days = 0

  tags = {
    Environment = var.env
  }
}

resource "aws_secretsmanager_secret_version" "config" {
  secret_id = aws_secretsmanager_secret.config.id
  secret_string = jsonencode({
    EMAIL_VERIFICATION_QUEUE_URL = aws_sqs_queue.journal_queue.url
    DB_ENDPOINT                  = aws_rds_cluster.aurora.endpoint
    DB_NAME                      = aws_rds_cluster.aurora.database_name
    REDIS_URL                    = "rediss://${aws_elasticache_serverless_cache.valkey.endpoint[0].address}:${aws_elasticache_serverless_cache.valkey.endpoint[0].port}"
  })
}
