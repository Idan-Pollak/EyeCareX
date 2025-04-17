from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_iam as iam,
    Duration
)
from constructs import Construct
import os

class BedrockLambdaStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create IAM role for Lambda
        lambda_role = iam.Role(
            self, "BedrockLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )

        # Add Bedrock permissions
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=["*"]
            )
        )

        # Get the absolute path to the lambda directory
        lambda_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lambda")

        # Create Lambda function
        bedrock_lambda = _lambda.Function(
            self, "BedrockHandler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="bedrock_handler.lambda_handler",
            code=_lambda.Code.from_asset(lambda_dir),
            role=lambda_role,
            timeout=Duration.seconds(30),
            memory_size=256
        )

        # Output the Lambda function ARN
        self.lambda_arn = bedrock_lambda.function_arn 