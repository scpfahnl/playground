resource "aws_sqs_queue" "tfa_dlq" {
  name = "${var.env}-tfa-dlq"

  tags = {
    Environment = var.env
  }
}

resource "aws_sqs_queue" "tfa" {
  name                       = "${var.env}-tfa"
  visibility_timeout_seconds = 600
  receive_wait_time_seconds  = 20

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.tfa_dlq.arn
    maxReceiveCount     = 3
  })

  tags = {
    Environment = var.env
  }
}
