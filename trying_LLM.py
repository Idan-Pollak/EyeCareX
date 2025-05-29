import streamlit as st
import boto3
import json
from datetime import datetime
import re
from botocore.exceptions import ClientError
import jwt
from jwt.algorithms import RSAAlgorithm
import requests
from urllib.parse import urlparse
import hashlib
import hmac
import base64

# --- Page config ---
st.set_page_config(page_title="Eyecare X Chatbot", layout="wide")

# --- AWS Cognito Configuration ---
COGNITO_REGION = "us-east-1"
COGNITO_USER_POOL_ID = st.secrets["COGNITO_USER_POOL_ID"]
COGNITO_CLIENT_ID = st.secrets["COGNITO_CLIENT_ID"]
COGNITO_CLIENT_SECRET = st.secrets["COGNITO_CLIENT_SECRET"]

def calculate_secret_hash(username):
    message = username + COGNITO_CLIENT_ID
    dig = hmac.new(
        COGNITO_CLIENT_SECRET.encode('utf-8'),
        msg=message.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    return base64.b64encode(dig).decode()

# Initialize Cognito client
cognito_client = boto3.client(
    "cognito-idp",
    region_name=COGNITO_REGION,
    aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"]
)

# --- Input Validation Functions ---
def validate_prescription(text):
    # Remove any potentially harmful characters
    text = re.sub(r'[<>]', '', text)
    # Limit length
    if len(text) > 1000:
        return False, "Prescription text is too long"
    return True, text

def validate_treatment_plan(text):
    # Remove any potentially harmful characters
    text = re.sub(r'[<>]', '', text)
    # Limit length
    if len(text) > 1000:
        return False, "Treatment plan text is too long"
    return True, text

def validate_user_input(text):
    # Remove any potentially harmful characters
    text = re.sub(r'[<>]', '', text)
    # Limit length
    if len(text) > 500:
        return False, "Message is too long"
    return True, text

# --- Authentication Functions ---
def get_cognito_public_keys():
    keys_url = f'https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/jwks.json'
    response = requests.get(keys_url)
    return response.json()['keys']

def verify_token(token):
    try:
        headers = jwt.get_unverified_header(token)
        keys = get_cognito_public_keys()
        key = next((k for k in keys if k['kid'] == headers['kid']), None)
        
        if not key:
            return False, "Invalid token"
            
        public_key = RSAAlgorithm.from_jwk(json.dumps(key))
        payload = jwt.decode(
            token,
            public_key,
            algorithms=['RS256'],
            audience=COGNITO_CLIENT_ID
        )
        return True, payload
    except Exception as e:
        return False, str(e)

# --- Session State Initialization ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "access_token" not in st.session_state:
    st.session_state.access_token = None

# --- Authentication UI ---
if not st.session_state.authenticated:
    st.title("Eyecare X Access")
    
    tab1, tab2, tab3 = st.tabs(["Login", "Register", "Verify"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                try:
                    response = cognito_client.initiate_auth(
                        ClientId=COGNITO_CLIENT_ID,
                        AuthFlow='USER_PASSWORD_AUTH',
                        AuthParameters={
                            'USERNAME': username,
                            'PASSWORD': password,
                            'SECRET_HASH': calculate_secret_hash(username)
                        }
                    )
                    
                    st.session_state.access_token = response['AuthenticationResult']['AccessToken']
                    st.session_state.authenticated = True
                    st.rerun()
                except ClientError as e:
                    st.error(f"Authentication failed: {str(e)}")
    
    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            email = st.text_input("Email")
            register = st.form_submit_button("Register")
            
            if register:
                try:
                    response = cognito_client.sign_up(
                        ClientId=COGNITO_CLIENT_ID,
                        Username=new_username,
                        Password=new_password,
                        SecretHash=calculate_secret_hash(new_username),
                        UserAttributes=[
                            {'Name': 'email', 'Value': email}
                        ]
                    )
                    st.success("Registration successful! Please check your email for verification code and use the 'Verify' tab to confirm your account.")
                except ClientError as e:
                    st.error(f"Registration failed: {str(e)}")
    
    with tab3:
        with st.form("verify_form"):
            verify_username = st.text_input("Username")
            verification_code = st.text_input("Verification Code")
            verify = st.form_submit_button("Verify Account")
            
            if verify:
                try:
                    response = cognito_client.confirm_sign_up(
                        ClientId=COGNITO_CLIENT_ID,
                        Username=verify_username,
                        ConfirmationCode=verification_code,
                        SecretHash=calculate_secret_hash(verify_username)
                    )
                    st.success("Account verified successfully! You can now log in.")
                except ClientError as e:
                    st.error(f"Verification failed: {str(e)}")
    
    st.stop()

# --- AWS Lambda setup with API Gateway ---
lambda_client = boto3.client(
    "lambda",
    region_name="us-east-1",
    aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"]
)

# --- Session State Initialization ---
for key in ["messages", "prescription", "treatment_plan", "prescription_explained"]:
    if key not in st.session_state:
        st.session_state[key] = [] if key == "messages" else (False if key == "prescription_explained" else "")

# --- CSS Styles ---
st.markdown("""
<style>
    .header {
        text-align: center;
        background-color: #2c3e50;
        color: white;
        font-size: 2rem;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .message {
        padding: 10px;
        border-radius: 15px;
        margin: 10px 0;
        max-width: 80%;
        word-wrap: break-word;
    }
    .user-message {
        background-color: #3498db;
        color: white;
        margin-right: auto;
    }
    .assistant-message {
        background-color: #f0f2f5;
        color: black;
        margin-left: auto;
    }
    .message-time {
        font-size: 0.7rem;
        color: #7f8c8d;
        text-align: right;
    }
</style>
""", unsafe_allow_html=True)

# --- Layout ---
col1, col2 = st.columns([3, 1])

# --- Sidebar Section ---
with col2:
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.access_token = None
        st.rerun()

    if st.button("Reset Chat"):
        st.session_state.messages = []
        st.session_state.prescription = ""
        st.session_state.treatment_plan = ""
        st.session_state.prescription_explained = False
        st.rerun()

    st.subheader("Diagnosis")
    new_prescription = st.text_area("Enter diagnosis:", value=st.session_state.prescription, height=150)

    st.subheader("Treatment Plan")
    new_treatment_plan = st.text_area("Enter treatment plan:", value=st.session_state.treatment_plan, height=150)

    if st.button("Finish"):
        # Validate inputs
        prescription_valid, prescription_msg = validate_prescription(new_prescription)
        treatment_valid, treatment_msg = validate_treatment_plan(new_treatment_plan)
        
        if prescription_valid and treatment_valid:
            st.session_state.prescription = prescription_msg
            st.session_state.treatment_plan = treatment_msg
            st.session_state.messages = []
            st.session_state.prescription_explained = False
            st.rerun()
        else:
            if not prescription_valid:
                st.error(prescription_msg)
            if not treatment_valid:
                st.error(treatment_msg)

# --- Chat Section ---
with col1:
    st.markdown('<div class="header">Eyecare X Chat Assistant</div>', unsafe_allow_html=True)

    if not st.session_state.messages:
        st.markdown("""
        <div class="message assistant-message">
            Hello! I'm your Eyecare X Assistant. Once you enter your diagnosis and treatment plan, I'll help explain them.
            <div class="message-time">Today</div>
        </div>
        """, unsafe_allow_html=True)

    for msg in st.session_state.messages:
        role_class = "user-message" if msg["role"] == "user" else "assistant-message"
        st.markdown(f"""
        <div class="message {role_class}">
            {msg["content"]}
            <div class="message-time">{msg.get("time", datetime.now().strftime('%H:%M'))}</div>
        </div>
        """, unsafe_allow_html=True)

    user_input = st.chat_input("Ask a follow-up question...")

# --- Lambda Helper Function ---
def query_lambda(prompt: str) -> str:
    # Validate input
    is_valid, validated_prompt = validate_user_input(prompt)
    if not is_valid:
        raise ValueError(validated_prompt)

    lambda_payload = {
        "prompt": validated_prompt,
        "max_tokens": 1000,
        "temperature": 0.3,
        "top_k": 250,
        "top_p": 1,
        "stop_sequences": ["\n\nHuman:"],
        "access_token": st.session_state.access_token  # Include token for authorization
    }

    try:
        function_name = "BedrockLambdaStack-EducationChatLambda8A98495D-if9qfRQ8YnCe"
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(lambda_payload)
        )
        
        response_payload = json.loads(response['Payload'].read())
        
        if response_payload.get("statusCode") == 200:
            return json.loads(response_payload['body'])['completion']
        else:
            raise Exception(f"Lambda error: {response_payload.get('body', 'Unknown error')}")
    except Exception as e:
        raise Exception(f"Lambda invocation error: {str(e)}")

# --- Initial Explanation ---
if st.session_state.prescription and st.session_state.treatment_plan and not st.session_state.prescription_explained:
    base_prompt = (
        "\n\nHuman: You are an optometrist explaining a diagnosis and treatment plan to a patient with no optometry knowledge.\n"
        f"Diagnosis: {st.session_state.prescription}\n"
        f"Treatment Plan: {st.session_state.treatment_plan}\n"
        "Please explain the above in simple terms and ask if the patient has any questions.\n\nAssistant:"
    )

    try:
        response_text = query_lambda(base_prompt)
        st.session_state.messages.append({
            "role": "assistant",
            "content": response_text,
            "time": datetime.now().strftime("%H:%M")
        })
        st.session_state.prescription_explained = True
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")

# --- Handle Follow-up ---
if user_input:
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "time": datetime.now().strftime("%H:%M")
    })

    followup_prompt = (
        "\n\nHuman: You are an optometrist explaining a diagnosis and treatment plan to a patient with no optometry knowledge.\n"
        f"Diagnosis: {st.session_state.prescription}\n"
        f"Treatment Plan: {st.session_state.treatment_plan}\n"
        "Please explain the above in simple terms and ask if the patient has any questions.\n\n"
    )

    for msg in st.session_state.messages:
        role = "Human" if msg["role"] == "user" else "Assistant"
        followup_prompt += f"{role}: {msg['content'].strip()}\n\n"
    followup_prompt += "Assistant:"

    try:
        response_text = query_lambda(followup_prompt)
        st.session_state.messages.append({
            "role": "assistant",
            "content": response_text,
            "time": datetime.now().strftime("%H:%M")
        })
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")
