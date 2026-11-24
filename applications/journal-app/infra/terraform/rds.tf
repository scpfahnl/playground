resource "aws_security_group" "aurora" {
  name        = "${var.env}-journal-aurora"
  description = "Aurora access from EKS pods"
  vpc_id      = data.aws_eks_cluster.main.vpc_config[0].vpc_id

  ingress {
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [data.aws_eks_cluster.main.vpc_config[0].cluster_security_group_id]
  }

  tags = {
    Environment = var.env
  }
}

resource "aws_db_subnet_group" "aurora" {
  name       = "${var.env}-journal-aurora"
  subnet_ids = data.aws_eks_cluster.main.vpc_config[0].subnet_ids

  tags = {
    Environment = var.env
  }
}

resource "aws_rds_cluster" "aurora" {
  cluster_identifier         = "${var.env}-journal-aurora-cluster"
  engine                     = "aurora-mysql"
  engine_version             = "8.4.mysql_aurora.8.4.8"
  database_name              = "journal"
  master_username            = "admin"
  master_password_wo         = ephemeral.random_password.db_master.result
  master_password_wo_version = 1
  port                       = 3306
  db_subnet_group_name       = aws_db_subnet_group.aurora.name
  vpc_security_group_ids     = [aws_security_group.aurora.id]
  skip_final_snapshot        = true

  serverlessv2_scaling_configuration {
    min_capacity = 0.5
    max_capacity = 2
  }

  tags = {
    Environment = var.env
  }
}

resource "aws_rds_cluster_instance" "aurora" {
  identifier         = "${var.env}-journal-aurora-instance"
  cluster_identifier = aws_rds_cluster.aurora.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.aurora.engine
  engine_version     = aws_rds_cluster.aurora.engine_version

  tags = {
    Environment = var.env
  }
}
