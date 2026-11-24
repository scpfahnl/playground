data "aws_iam_policy_document" "keda" {
  statement {
    effect    = "Allow"
    actions   = ["sqs:GetQueueAttributes"]
    resources = [aws_sqs_queue.journal_queue.arn]
  }
}

resource "aws_iam_role_policy" "keda" {
  name   = "${var.env}-journal-keda"
  role   = data.aws_iam_role.keda.name
  policy = data.aws_iam_policy_document.keda.json
}

data "aws_iam_policy_document" "external_secrets" {
  statement {
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret",
      "secretsmanager:GetResourcePolicy",
      "secretsmanager:ListSecretVersionIds",
    ]
    resources = [
      aws_secretsmanager_secret.api_jwt_signing_key.arn,
      aws_secretsmanager_secret.db_master.arn,
      aws_secretsmanager_secret.config.arn,
    ]
  }
}

resource "aws_iam_role_policy" "external_secrets" {
  name   = "${var.env}-journal-external-secrets"
  role   = data.aws_iam_role.external_secrets.name
  policy = data.aws_iam_policy_document.external_secrets.json
}
