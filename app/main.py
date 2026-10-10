import os
import time
from dotenv import load_dotenv
import streamlit as st

# Attempt to import Groq SDK
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

# Load local environment variables from .env
load_dotenv()

APP_TITLE = os.getenv("APP_TITLE", "AWS EKS Q&A Chatbot")
APP_ENV = os.getenv("APP_ENV", "development")
ENV_GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Page Configuration
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="⚡",
    layout="wide"
)

# Sidebar Configuration
with st.sidebar:
    st.header("⚡ Model Configuration")

    # Groq API Key Handling (from .env or Sidebar input)
    if ENV_GROQ_API_KEY:
        groq_api_key = ENV_GROQ_API_KEY
        st.success("🔑 Groq API Key loaded from environment")
    else:
        groq_api_key = st.text_input(
            "Groq API Key",
            type="password",
            placeholder="gsk_...",
            help="Enter your Groq API key here or configure GROQ_API_KEY in .env / Kubernetes Secret"
        )
        if not groq_api_key:
            st.info("💡 Tip: Enter a Groq API key to enable live AI responses, or continue in Demo Mode.")

    st.divider()

    # Model Selection
    model_options = [
        "llama-3.3-70b-versatile",
        "deepseek-r1-distill-llama-70b",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
        "gpt-120b",
        "Custom Model"
    ]

    selected_option = st.selectbox(
        "Select AI Model:",
        options=model_options,
        index=0,
        help="Choose a Groq hosted model or specify custom model"
    )

    if selected_option == "Custom Model":
        active_model = st.text_input("Enter Model Identifier:", value="gpt-120b")
    else:
        active_model = selected_option

    # Generation Parameters
    with st.expander("⚙️ Advanced Parameters", expanded=False):
        temperature = st.slider("Temperature", min_value=0.0, max_value=1.5, value=0.7, step=0.1)
        max_tokens = st.slider("Max Tokens", min_value=128, max_value=4096, value=1024, step=128)

    st.divider()

    # System Status
    st.subheader("🖥️ Platform Status")
    st.markdown(f"**Application:** `{APP_TITLE}`")
    st.markdown(f"**Environment:** `{APP_ENV}`")
    st.markdown(f"**Active Model:** `{active_model}`")
    st.markdown("**Platform:** `Amazon EKS (Kubernetes)`")
    st.markdown("**Nodes:** `Private Subnets (via NAT Gateway)`")
    st.markdown("**Ingress:** `AWS Application Load Balancer`")

    st.divider()

    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# Main Header
st.title(f"⚡ {APP_TITLE}")
st.caption(f"Running on Private AWS EKS Worker Nodes • Active Model: `{active_model}`")

# Initialize Chat Messages in session state
if "messages" not in st.session_state or not st.session_state.messages:
    welcome_content = (
        f"👋 **Welcome to the AWS EKS Q&A Chatbot!**\n\n"
        f"Active model is set to **`{active_model}`** via Groq.\n\n"
        f"Ask me any question about AWS EKS, ALB networking, Kubernetes, or general topics!"
    )
    if not groq_api_key:
        welcome_content += (
            "\n\n> ⚠️ **Note:** No Groq API Key detected. Add your key in the sidebar for live AI responses, "
            "or test with simulated demo mode."
        )

    st.session_state.messages = [
        {"role": "assistant", "content": welcome_content}
    ]

# Display Existing Chat Messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Simulated Fallback Response (Used when API key is not provided)
def get_fallback_simulated_response(question: str) -> str:
    return (
        f"**[Demo Mode Response (Key not provided)]**\n\n"
        f"You asked: *\"{question}\"*\n\n"
        f"To get live AI answers with model **`{active_model}`**, please enter your **Groq API Key** in the sidebar "
        f"or configure the `GROQ_API_KEY` environment variable in Kubernetes/`.env`."
    )

# Handle User Input
if user_prompt := st.chat_input("Ask a question..."):
    # Append user question
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # Generate Assistant Response
    with st.chat_message("assistant"):
        if groq_api_key and GROQ_AVAILABLE:
            try:
                client = Groq(api_key=groq_api_key)

                # Format conversation history for Groq API
                api_messages = [
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful, expert AWS DevOps and Kubernetes AI assistant "
                            "running on a containerized Streamlit application inside an Amazon EKS private cluster. "
                            "Provide accurate, clear, and concise technical answers."
                        )
                    }
                ]

                # Append recent messages (excluding system)
                for msg in st.session_state.messages[-10:]:
                    if msg["role"] in ["user", "assistant"]:
                        api_messages.append({"role": msg["role"], "content": msg["content"]})

                # Stream response from Groq
                response_stream = client.chat.completions.create(
                    model=active_model,
                    messages=api_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True
                )

                # Stream to UI
                def generate_chunks():
                    for chunk in response_stream:
                        if chunk.choices and chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content

                assistant_reply = st.write_stream(generate_chunks())

            except Exception as e:
                error_msg = f"⚠️ **Groq API Error:** {str(e)}"
                st.error(error_msg)
                assistant_reply = error_msg
        else:
            # Fallback when key is missing or groq library not installed
            with st.spinner("Generating response..."):
                time.sleep(0.4)
                assistant_reply = get_fallback_simulated_response(user_prompt)
                st.markdown(assistant_reply)

    # Save assistant message to chat history
    st.session_state.messages.append({"role": "assistant", "content": assistant_reply})
