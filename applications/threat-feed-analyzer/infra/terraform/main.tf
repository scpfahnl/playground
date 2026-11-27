module "api_pod_identity" {
  source  = "terraform-aws-modules/eks-pod-identity/aws"
  version = "2.9.0"

  name            = "${var.env}-tfa-api-role"
  use_name_prefix = false

  attach_custom_policy = true
  policy_statements = [
    {
      actions = [
        "sqs:SendMessage",
        "sqs:GetQueueAttributes",
      ]
      resources = [aws_sqs_queue.tfa.arn]
    }
  ]

  associations = {
    api = {
      cluster_name    = data.aws_eks_cluster.main.name
      namespace       = "threat-feed-analyzer"
      service_account = "api"
    }
  }

  tags = {
    Environment = var.env
  }
}

module "worker_pod_identity" {
  source  = "terraform-aws-modules/eks-pod-identity/aws"
  version = "2.9.0"

  name            = "${var.env}-tfa-worker-role"
  use_name_prefix = false

  attach_custom_policy = true
  policy_statements = [
    {
      actions = [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
      ]
      resources = [aws_sqs_queue.tfa.arn]
    }
  ]

  associations = {
    worker = {
      cluster_name    = data.aws_eks_cluster.main.name
      namespace       = "threat-feed-analyzer"
      service_account = "worker"
    }
  }

  tags = {
    Environment = var.env
  }
}
