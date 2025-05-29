from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_apigateway as apigateway,
    aws_cognito as cognito,
    Duration,
    RemovalPolicy,
    CfnOutput
)
from constructs import Construct
import os

class BedrockLambdaStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create Cognito User Pool
        user_pool = cognito.UserPool(
            self, "EyecareXUserPool",
            user_pool_name="eyecare-x-users",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(
                email=True,
                username=True
            ),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(
                    required=True,
                    mutable=True
                )
            ),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY
        )

        # Create Cognito App Client
        app_client = user_pool.add_client(
            "EyecareXAppClient",
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True
            ),
            prevent_user_existence_errors=True,
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(
                    authorization_code_grant=True
                ),
                callback_urls=["https://your-domain.com/callback"],
                logout_urls=["https://your-domain.com/logout"]
            )
        )

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

        # Add Cognito permissions
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "cognito-idp:GetUser",
                    "cognito-idp:AdminGetUser"
                ],
                resources=[user_pool.user_pool_arn]
            )
        )

        # Get absolute path to the lambda directory
        lambda_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lambda")

        # Create Lambda function
        chat_lambda = _lambda.Function(
            self, "EducationChatLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="bedrock_handler.chat_handler",
            code=_lambda.Code.from_asset(lambda_dir),
            role=lambda_role,
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "COGNITO_REGION": "us-east-1",
                "COGNITO_USER_POOL_ID": "us-east-1_qiiupLb1p",
                "COGNITO_CLIENT_ID": "1tfio3mc0stp1ldeqajko1cii7"
            }
        )

        # Create API Gateway
        api = apigateway.RestApi(
            self, "EyecareXApi",
            rest_api_name="Eyecare X API",
            description="API for Eyecare X application",
            deploy_options=apigateway.StageOptions(
                stage_name="prod",
                throttling_rate_limit=100,
                throttling_burst_limit=50,
                logging_level=apigateway.MethodLoggingLevel.OFF,
                data_trace_enabled=False,
                metrics_enabled=True
            ),
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization"],
                max_age=Duration.days(1)
            )
        )

        # Create Cognito Authorizer
        authorizer = apigateway.CognitoUserPoolsAuthorizer(
            self, "CognitoAuthorizer",
            cognito_user_pools=[user_pool]
        )

        # Create API Gateway integration
        chat_integration = apigateway.LambdaIntegration(
            chat_lambda,
            proxy=True,
            integration_responses=[
                apigateway.IntegrationResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": "'*'"
                    }
                )
            ]
        )

        # Add resource and method with authorizer
        chat_resource = api.root.add_resource("chat")
        chat_resource.add_method(
            "POST",
            chat_integration,
            authorizer=authorizer,
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True
                    }
                ),
                apigateway.MethodResponse(
                    status_code="401",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True
                    }
                ),
                apigateway.MethodResponse(
                    status_code="429",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True
                    }
                )
            ]
        )

        # Output important values
        CfnOutput(
            self, "UserPoolId",
            value=user_pool.user_pool_id,
            description="Cognito User Pool ID"
        )

        CfnOutput(
            self, "UserPoolClientId",
            value=app_client.user_pool_client_id,
            description="Cognito App Client ID"
        )

        CfnOutput(
            self, "ApiEndpoint",
            value=api.url,
            description="API Gateway endpoint URL"
        )
