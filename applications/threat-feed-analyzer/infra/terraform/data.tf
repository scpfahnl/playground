data "aws_eks_cluster" "main" {
  name = "${var.env}-playground-cluster"
}

data "aws_iam_role" "keda" {
  name = "${var.env}-playground-keda-role"
}

data "aws_iam_role" "external_secrets" {
  name = "${var.env}-playground-external-secrets-role"
}
