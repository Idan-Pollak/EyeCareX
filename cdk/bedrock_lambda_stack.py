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

        # Create IAM role for both Lambda functions
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

        # Get absolute path to the lambda directory
        lambda_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lambda")

        # Create Chat Lambda function
        chat_lambda = _lambda.Function(
            self, "EducationChatLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="bedrock_handler.chat_handler",  # 👈 Chat handler
            code=_lambda.Code.from_asset(lambda_dir),
            role=lambda_role,
            timeout=Duration.seconds(30),
            memory_size=256
        )

        # Create Summary Lambda function
        summary_lambda = _lambda.Function(
            self, "EducationSummaryLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="bedrock_handler.summary_handler",  # 👈 Summary handler
            code=_lambda.Code.from_asset(lambda_dir),
            role=lambda_role,
            timeout=Duration.seconds(30),
            memory_size=256
        )

        # Optional: Store ARNs for both functions
        self.chat_lambda_arn = chat_lambda.function_arn
        self.summary_lambda_arn = summary_lambda.function_arn
