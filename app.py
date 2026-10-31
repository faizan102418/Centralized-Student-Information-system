"""Streamlit UI for the Student Record Chatbot, with login + RBAC.

Run with: streamlit run app.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import streamlit as st

from chatbot.auth import authenticate
from chatbot.llm_client import GroqAPIError
from chatbot.rag_pipeline import answer_question, setup_vector_db

st.set_page_config(page_title="Student Record Chatbot", page_icon="🎓")

if "user" not in st.session_state:
    st.session_state.user = None

# --- Login gate ---
if st.session_state.user is None:
    st.title("🔐 Log in")
    st.caption("Student Record Chatbot")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")

    if submitted:
        user = authenticate(username, password)
        if user:
            st.session_state.user = user
            st.rerun()
        else:
            st.error("Invalid username or password.")

    st.info(
        "Demo accounts (see data/seed.sql): "
        "**admin** / admin123 · **faculty1** / faculty123 · "
        "**alice** / alice123 (student, own-record access only)"
    )
    st.stop()

# --- Authenticated area ---
user = st.session_state.user

with st.sidebar:
    st.write(f"Logged in as **{user['username']}**")
    st.caption(f"Role: {user['role']}")
    if user["role"] == "student":
        st.caption(f"Linked record: {user.get('student_name', 'n/a')}")
    if st.button("Log out"):
        st.session_state.user = None
        st.session_state.messages = []
        st.rerun()

st.title("🎓 Student Record Chatbot")
st.markdown(
    "Ask me about a student by name (e.g., *'What is Alice Smith's discipline?'*). "
    "You can also ask general questions."
)


@st.cache_resource
def load_vector_db():
    with st.spinner("Loading student data and setting up knowledge base..."):
        return setup_vector_db()


try:
    vectorstore = load_vector_db()
except Exception as exc:  # noqa: BLE001
    st.error(f"Failed to load knowledge base: {exc}")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask a question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = answer_question(vectorstore, prompt, user=user)
                st.markdown(response)
            except GroqAPIError:
                response = (
                    "The AI service is temporarily unavailable. "
                    "Please try again in a little while."
                )
                st.error(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
