import streamlit as st
import boto3
import json
from datetime import datetime

# Page config
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
if "selected_disease" not in st.session_state:
    st.session_state.selected_disease = "None"
if "severity" not in st.session_state:
    st.session_state.severity = "Mild"
if "prescription" not in st.session_state:
    st.session_state.prescription = ""

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
    .chat-box {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        height: 500px;
        overflow-y: auto;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 10px;
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

# --- Layout: Chat Center - Sidebar Right ---
col1, col2 = st.columns([3, 1])

# --- Chat Section ---
with col1:
    st.markdown('<div class="header">Eyecare X Chat Assistant</div>', unsafe_allow_html=True)

    if not st.session_state.messages:
        st.markdown("""
        <div class="message assistant-message">
            Hello! I'm your Eyecare X Assistant. How can I help you today?
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

    user_input = st.chat_input("Type your message and press Enter")

# --- Sidebar Section ---
with col2:
    st.subheader("Patient Info")

    st.session_state.selected_disease = st.selectbox(
        "Eye Condition",
        ["None", "Cataracts", "Glaucoma", "AMD", "Dry Eye", "Conjunctivitis"],
        index=["None", "Cataracts", "Glaucoma", "AMD", "Dry Eye", "Conjunctivitis"].index(st.session_state.selected_disease)
    )

    st.session_state.severity = st.selectbox(
        "Eye Condition Severity",
        ["Mild", "Moderate", "Severe", "Very Severe"],
        index=["Mild", "Moderate", "Severe", "Very Severe"].index(st.session_state.severity)
    )

    st.session_state.prescription = st.text_input("Prescription", value=st.session_state.prescription)

    if st.button("🪼 Reset Chat"):
        st.session_state.messages = []
        st.session_state.selected_disease = "None"
        st.session_state.severity = "Mild"
        st.session_state.prescription = ""
        st.rerun()

# --- Process Input ---
if user_input:
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "time": datetime.now().strftime("%H:%M")
    })

    system_context = ""
    if st.session_state.selected_disease != "None":
        system_context += f"Patient has been diagnosed with {st.session_state.selected_disease}, severity: {st.session_state.severity}. "
    if st.session_state.prescription:
        system_context += f"Patient prescription: {st.session_state.prescription}. "

    prompt = f"{system_context}\n\n"
    for msg in st.session_state.messages:
        role = "Human" if msg["role"] == "user" else "Assistant"
        prompt += f"{role}: {msg['content']}\n\n"
    prompt += "Assistant:"

    lambda_payload = {
        "prompt": prompt,
        "max_tokens_to_sample": 200,
        "temperature": 0.1,
        "top_k": 250,
        "top_p": 1,
        "stop_sequences": ["\n\nHuman:"]
    }

    try:
        response = lambda_client.invoke(
            FunctionName='ChatLambda59BC07ED',
            InvocationType='RequestResponse',
            Payload=json.dumps(lambda_payload)
        )

        response_payload = json.loads(response['Payload'].read())
        if response_payload.get('statusCode') == 200:
            output = json.loads(response_payload['body'])['completion']

            sentences = output.split(". ")
            output = ". ".join(sentences[:5]) + ("." if len(sentences) > 5 else "")

            st.session_state.messages.append({
                "role": "assistant",
                "content": output,
                "time": datetime.now().strftime("%H:%M")
            })
        else:
            st.error(f"Lambda Error: {response_payload.get('body', 'Unknown error')}")

        st.rerun()

    except Exception as e:
        st.error(f"Error: {str(e)}")

# --- End Conversation + Doctor Summary ---
if st.button("End Conversation"):
    full_chat = ""
    for msg in st.session_state.messages:
        role = "Human" if msg["role"] == "user" else "Assistant"
        full_chat += f"{role}: {msg['content']}\n\n"

    summary_prompt = (
        f"Summarize the following eyecare conversation between a patient and an assistant "
        f"in 2-3 sentences for a doctor to review:\n\n{full_chat}Human: Please summarize the conversation.\n\nAssistant:"
    )

    summary_payload = {
        "prompt": summary_prompt,
        "max_tokens_to_sample": 150,
        "temperature": 0.1,
        "top_k": 100,
        "top_p": 0.9,
        "stop_sequences": ["\n\nHuman:"]
    }

    try:
        summary_response = lambda_client.invoke(
            FunctionName='ChatLambda59BC07ED',
            InvocationType='RequestResponse',
            Payload=json.dumps(summary_payload)
        )

        summary_payload = json.loads(summary_response['Payload'].read())
        if summary_payload.get('statusCode') == 200:
            summary_text = json.loads(summary_payload['body'])['completion']

            st.subheader("Doctor Summary Preview")
            st.write(summary_text)
        else:
            st.error(f"Lambda Error: {summary_payload.get('body', 'Unknown error')}")

    except Exception as e:
        st.error(f"Error generating summary: {str(e)}")
