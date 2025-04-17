#!/usr/bin/env python3
import aws_cdk as cdk
from bedrock_lambda_stack import BedrockLambdaStack

app = cdk.App()
BedrockLambdaStack(app, "BedrockLambdaStack")

app.synth() 