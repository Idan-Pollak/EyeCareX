import json
import boto3
import os

def lambda_handler(event, context):
    try:
        # Initialize Bedrock client
        bedrock = boto3.client(
            "bedrock-runtime",
            region_name="us-east-1"
        )
        
        # Extract parameters from event
        prompt = event.get('prompt')
        max_tokens = event.get('max_tokens_to_sample', 200)
        temperature = event.get('temperature', 0.1)
        top_k = event.get('top_k', 250)
        top_p = event.get('top_p', 1)
        stop_sequences = event.get('stop_sequences', ["\n\nHuman:"])
        
        # Prepare Bedrock request
        body = {
            "prompt": prompt,
            "max_tokens_to_sample": max_tokens,
            "temperature": temperature,
            "top_k": top_k,
            "top_p": top_p,
            "stop_sequences": stop_sequences
        }
        
        # Call Bedrock
        response = bedrock.invoke_model(
            body=json.dumps(body),
            modelId="anthropic.claude-v2",
            accept='application/json',
            contentType='application/json'
        )
        
        # Parse and return response
        output = json.loads(response['body'].read())["completion"].strip()
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'completion': output
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        } 