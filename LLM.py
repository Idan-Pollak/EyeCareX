import streamlit as st
import boto3
import json
import os

# Set AWS credentials
aws_access_key_id = "AKIAQKKPJHKHBOZP5M7U"
aws_secret_access_key = "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"

os.environ["AWS_ACCESS_KEY_ID"] = aws_access_key_id
os.environ["AWS_SECRET_ACCESS_KEY"] = aws_secret_access_key

# Initialize Bedrock client
bedrock = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-east-1'
)

model_id = "anthropic.claude-v2"

# Streamlit config
st.set_page_config(page_title="Claude Chatbot", page_icon="💬", layout="centered")

# Custom CSS for gray background and white text
st.markdown("""
    <style>
    body, .stApp {
        background-color: #2e2e2e;
        color: white;
    }
    .chat-bubble {
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 8px;
        max-width: 90%;
    }
    .user {
        background-color: #4a90e2;
        color: white;
        align-self: flex-end;
    }
    .assistant {
        background-color: #6e6e6e;
        color: white;
        align-self: flex-start;
    }
    </style>
""", unsafe_allow_html=True)

st.title("👁️ Eyecare X Chatbot")

# Reset chat option
if st.button("🧹 Reset Chat"):
    st.session_state.messages = []
    st.rerun()

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    role_class = "user" if msg["role"] == "user" else "assistant"
    name = "You" if msg["role"] == "user" else "Claude"
    st.markdown(
        f"<div class='chat-bubble {role_class}'><strong>{name}:</strong> {msg['content']}</div>",
        unsafe_allow_html=True
    )

# Top 20 eye diseases in Canada
eye_diseases = [
    "Cataracts", "Glaucoma", "Age-related macular degeneration",
    "Diabetic retinopathy", "Dry eye disease", "Conjunctivitis (Pink Eye)",
    "Amblyopia (Lazy Eye)", "Strabismus", "Uveitis", "Blepharitis",
    "Refractive errors (Myopia, Hyperopia, Astigmatism)", "Retinal detachment",
    "Eye floaters", "Presbyopia", "Corneal ulcer", "Optic neuritis",
    "Ocular migraines", "Color blindness", "Keratoconus", "Retinitis pigmentosa"
]

st.markdown("#### Talk to our AI Optometrist:")
selected_disease = st.selectbox("Pick a topic:", [""] + eye_diseases)

# Prescription input
prescription_input = st.text_input("Optional: Enter your current eye prescription")

# Set default question based on dropdown
if selected_disease:
    default_question = f"Can you tell me about {selected_disease.lower()}?"
else:
    default_question = ""

# Main user message input
user_input = st.text_input("Type your message:", value=default_question, key="input")

# Handle "Send"
if st.button("Send") and user_input.strip() != "":
    # Combine prescription with user message
    if prescription_input.strip():
        user_message = f"My current prescription is: {prescription_input.strip()}. {user_input}"
    else:
        user_message = user_input

    # Add to chat history
    st.session_state.messages.append({"role": "user", "content": user_message})

    # Construct prompt
    prompt = ""
    for msg in st.session_state.messages:
        role = "Human" if msg["role"] == "user" else "Assistant"
        prompt += f"{role}: {msg['content']}\n\n"
    prompt += "Assistant:"

    body = {
        "prompt": prompt,
        "max_tokens_to_sample": 200,
        "temperature": 0.5,
        "top_k": 250,
        "top_p": 1,
        "stop_sequences": ["\n\nHuman:"]
    }

    try:
        response = bedrock.invoke_model(
            body=json.dumps(body),
            modelId=model_id,
            accept='application/json',
            contentType='application/json'
        )

        response_body = json.loads(response['body'].read())
        assistant_reply = response_body['completion'].strip()

        st.session_state.messages.append({"role": "assistant", "content": assistant_reply})
        st.rerun()

    except Exception as e:
        st.error(f"Error: {e}")
