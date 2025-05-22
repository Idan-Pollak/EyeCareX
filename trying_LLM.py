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

# --- Bedrock setup ---
bedrock = boto3.client(
    "bedrock-runtime",
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
    if st.button("Reset Chat"):
        st.session_state.messages = []
        st.session_state.prescription = ""
        st.session_state.treatment_plan = ""
        st.session_state.prescription_explained = False
        st.rerun()

    st.subheader("Doctor's Diagnosis")
    new_prescription = st.text_area("Enter patient diagnosis:", value=st.session_state.prescription, height=150)

    st.subheader("Patient Treatment Plan")
    new_treatment_plan = st.text_area("Enter treatment plan:", value=st.session_state.treatment_plan, height=150)

    if st.button("Finish"):
        if new_prescription.strip() and new_treatment_plan.strip():
            st.session_state.prescription = new_prescription
            st.session_state.treatment_plan = new_treatment_plan
            st.session_state.messages = []
            st.session_state.prescription_explained = False
            st.rerun()
        else:
            st.warning("Please complete both the diagnosis and treatment plan before submitting.")

# --- Chat Section ---
with col1:
    st.markdown('<div class="header">Eyecare X Chat Assistant</div>', unsafe_allow_html=True)

    if not st.session_state.messages:
        st.markdown("""
        <div class="message assistant-message">
            Hello! I'm your Eyecare X Assistant. Once the doctor enters your diagnosis and treatment plan, I'll help explain them.
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

# --- Bedrock Helper Function ---
def query_bedrock(prompt: str) -> str:
    model_id = "anthropic.claude-instant-v1"  # Or use another available model ID
    body = {
        "prompt": prompt,
        "max_tokens_to_sample": 250,
        "temperature": 0.3,
        "top_k": 250,
        "top_p": 1,
        "stop_sequences": ["\n\nHuman:"]
    }

    response = bedrock.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body)
    )

    response_body = json.loads(response['body'].read())
    return response_body['completion']

# --- Initial Explanation ---
if st.session_state.prescription and st.session_state.treatment_plan and not st.session_state.prescription_explained:
    base_prompt = (
        "\n\nHuman: You are an optometrist explaining a diagnosis and treatment plan to a patient with no optometry knowledge.\n"
        f"Diagnosis: {st.session_state.prescription}\n"
        f"Treatment Plan: {st.session_state.treatment_plan}\n"
        "Please explain the above in simple terms and ask if the patient has any questions.\n\nAssistant:"
    )

    try:
        response_text = query_bedrock(base_prompt)
        st.session_state.messages.append({
            "role": "assistant",
            "content": response_text,
            "time": datetime.now().strftime("%H:%M")
        })
        st.session_state.prescription_explained = True
        st.rerun()
    except Exception as e:
        st.error(f"Bedrock Error: {e}")

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
        response_text = query_bedrock(followup_prompt)
        st.session_state.messages.append({
            "role": "assistant",
            "content": response_text,
            "time": datetime.now().strftime("%H:%M")
        })
        st.rerun()
    except Exception as e:
        st.error(f"Bedrock Error: {e}")
