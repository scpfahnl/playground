ephemeral "random_password" "db_master" {
  length  = 32
  special = false
}

resource "aws_secretsmanager_secret" "db_master" {
  name                    = "${var.env}/tfa/db-master"
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

resource "random_password" "opensearch_master" {
  length           = 32
  min_upper        = 1
  min_lower        = 1
  min_numeric      = 1
  min_special      = 1
  override_special = "_-"
}

resource "aws_secretsmanager_secret" "config" {
  name                    = "${var.env}/tfa/config"
  recovery_window_in_days = 0

  tags = {
    Environment = var.env
  }
}

resource "aws_secretsmanager_secret_version" "config" {
  secret_id = aws_secretsmanager_secret.config.id
  secret_string = jsonencode({
    QUEUE_URL      = aws_sqs_queue.tfa.url
    DB_ENDPOINT    = aws_rds_cluster.aurora.endpoint
    DB_NAME        = aws_rds_cluster.aurora.database_name
    OPENSEARCH_URL = "https://${aws_opensearch_domain.opensearch.advanced_security_options[0].master_user_options[0].master_user_name}:${random_password.opensearch_master.result}@${aws_opensearch_domain.opensearch.endpoint}"
  })
}
