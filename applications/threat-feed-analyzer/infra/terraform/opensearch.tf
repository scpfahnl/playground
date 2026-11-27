resource "aws_security_group" "opensearch" {
  name        = "${var.env}-tfa-opensearch"
  description = "OpenSearch access from EKS pods"
  vpc_id      = data.aws_eks_cluster.main.vpc_config[0].vpc_id

  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [data.aws_eks_cluster.main.vpc_config[0].cluster_security_group_id]
  }

  tags = {
    Environment = var.env
  }
}

resource "aws_opensearch_domain" "opensearch" {
  domain_name    = "${var.env}-tfa"
  engine_version = "OpenSearch_3.9"

  cluster_config {
    instance_type  = "t3.small.search"
    instance_count = 1
  }

  ebs_options {
    ebs_enabled = true
    volume_type = "gp3"
    volume_size = 10
  }

  vpc_options {
    subnet_ids         = [sort(data.aws_eks_cluster.main.vpc_config[0].subnet_ids)[0]]
    security_group_ids = [aws_security_group.opensearch.id]
  }

  encrypt_at_rest {
    enabled = true
  }

  node_to_node_encryption {
    enabled = true
  }

  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
  }

  advanced_security_options {
    enabled                        = true
    internal_user_database_enabled = true

    master_user_options {
      master_user_name     = "tfa"
      master_user_password = random_password.opensearch_master.result
    }
  }

  tags = {
    Environment = var.env
  }
}

resource "aws_opensearch_domain_policy" "opensearch" {
  domain_name = aws_opensearch_domain.opensearch.domain_name
  access_policies = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { AWS = "*" }
        Action    = "es:ESHttp*"
        Resource  = "${aws_opensearch_domain.opensearch.arn}/*"
      }
    ]
  })
}
