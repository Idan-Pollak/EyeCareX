import streamlit as st
import boto3
import json
from datetime import datetime

# --- Page config ---
st.set_page_config(page_title="Eyecare X Chatbot", layout="wide")

# --- Password Gate ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("Eyecare X Access")
    password_input = st.text_input("Enter Password:", type="password")
    if password_input == st.secrets["ACCESS_PASSWORD"]:
        st.session_state.authenticated = True
        st.rerun()
    elif password_input:
        st.error("Incorrect password. Please try again.")
    st.stop()

# --- AWS setup ---
lambda_client = boto3.client(
    "lambda",
    region_name="us-east-1",
    aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"]
)

# --- Session State Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "prescription" not in st.session_state:
    st.session_state.prescription = ""
if "prescription_explained" not in st.session_state:
    st.session_state.prescription_explained = False

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

# --- Chat Section ---
with col1:
    st.markdown('<div class="header">Eyecare X Chat Assistant</div>', unsafe_allow_html=True)

    if not st.session_state.messages:
        st.markdown("""
        <div class="message assistant-message">
            Hello! I'm your Eyecare X Assistant. Once the doctor enters your diagnosis, I'll help explain it.
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

# --- Sidebar Section ---
with col2:
    st.subheader("Doctor's Prescription")
    new_prescription = st.text_area(
        "Enter patient diagnosis:",
        value=st.session_state.prescription,
        height=150
    )

    if st.button("Reset Chat"):
        st.session_state.messages = []
        st.session_state.prescription = ""
        st.session_state.prescription_explained = False
        st.rerun()

# --- Update and explain prescription ---
if new_prescription.strip() and new_prescription != st.session_state.prescription:
    st.session_state.prescription = new_prescription
    st.session_state.messages = []
    st.session_state.prescription_explained = False
    st.rerun()

# --- Initial Explanation of Prescription ---
if st.session_state.prescription and not st.session_state.prescription_explained:
    prompt = (
        f"Help me explain this optometry diagnosis to a patient with no optometry knowledge. "
        f"The diagnosis is: {st.session_state.prescription}. "
        f"After explaining, ask the patient if they have any follow-up questions."
    )

    lambda_payload = {
        "prompt": prompt,
        "max_tokens": 250,
        "temperature": 0.3,
        "top_k": 250,
        "top_p": 1,
        "stop_sequences": ["\n\nHuman:"]
    }

    try:
        response = lambda_client.invoke(
            FunctionName='lambda',  
            InvocationType='RequestResponse',
            Payload=json.dumps(lambda_payload)
        )
        response_payload = json.loads(response['Payload'].read())
        if response_payload.get("statusCode") == 200:
            output = json.loads(response_payload['body'])['completion']
            st.session_state.messages.append({
                "role": "assistant",
                "content": output,
                "time": datetime.now().strftime("%H:%M")
            })
            st.session_state.prescription_explained = True
            st.rerun()
        else:
            st.error(f"Lambda error: {response_payload.get('body', 'Unknown error')}")
    except Exception as e:
        st.error(f"Error: {str(e)}")

# --- Handle Patient Follow-up ---
if user_input:
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "time": datetime.now().strftime("%H:%M")
    })

    # Construct the chat prompt
    prompt = ""
    for msg in st.session_state.messages:
        role = "Human" if msg["role"] == "user" else "Assistant"
        prompt += f"{role}: {msg['content']}\n\n"
    prompt += "Assistant:"

    lambda_payload = {
        "prompt": prompt,
        "max_tokens": 200,
        "temperature": 0.3,
        "top_k": 250,
        "top_p": 1,
        "stop_sequences": ["\n\nHuman:"]
    }

    try:
        response = lambda_client.invoke(
            FunctionName='lambda',  
            InvocationType='RequestResponse',
            Payload=json.dumps(lambda_payload)
        )

        response_payload = json.loads(response['Payload'].read())
        if response_payload.get("statusCode") == 200:
            output = json.loads(response_payload['body'])['completion']
            st.session_state.messages.append({
                "role": "assistant",
                "content": output,
                "time": datetime.now().strftime("%H:%M")
            })
            st.rerun()
        else:
            st.error(f"Lambda Error: {response_payload.get('body', 'Unknown error')}")

    except Exception as e:
        st.error(f"Error: {str(e)}")
