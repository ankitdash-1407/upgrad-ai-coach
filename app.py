import streamlit as st
from orchestrator import get_next_question, evaluate_turn, get_final_feedback

st.set_page_config(page_title="AI Mock Interview Coach", page_icon="🎙️", layout="centered")

# --- Initialize Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "evaluations" not in st.session_state:
    st.session_state.evaluations = []
if "turn_count" not in st.session_state:
    st.session_state.turn_count = 0
if "interview_active" not in st.session_state:
    st.session_state.interview_active = False
if "max_turns" not in st.session_state:
    st.session_state.max_turns = 5

st.title("🎙️ AI Mock Interview Coach")

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("Candidate Setup")
    role = st.text_input("Target Role", value="Data Analyst")
    focus = st.selectbox("Focus Area", ["Technical", "Behavioral", "Mixed (System Design + Behavioral)"])
    resume = st.text_area("Resume Snippet / Background (Optional)", 
                          value="Recently built a real-time anomaly detection engine using RAG.")
    turns = st.slider("Number of Questions", min_value=3, max_value=10, value=5)
    
    if st.button("Start Interview", type="primary"):
        # Reset State for a new interview
        st.session_state.messages = []
        st.session_state.evaluations = []
        st.session_state.turn_count = 0
        st.session_state.interview_active = True
        st.session_state.max_turns = turns
        
        # Generate the absolute first question
        with st.spinner("Preparing first question..."):
            first_q = get_next_question(role, resume, focus, chat_history=[], last_eval=None)
            st.session_state.messages.append({"role": "assistant", "content": first_q})

# --- Main Chat UI ---
# Render all previous chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input for the candidate
if st.session_state.interview_active:
    if prompt := st.chat_input("Type your answer here..."):
        # 1. Display Candidate's Answer
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 2. Silent Evaluation Step
        last_question = st.session_state.messages[-2]["content"] # The question they are answering
        with st.spinner("Evaluating answer..."):
            eval_data = evaluate_turn(role, last_question, prompt)
            st.session_state.evaluations.append(eval_data)
        
        st.session_state.turn_count += 1

        # 3. Check if interview is over
        if st.session_state.turn_count >= st.session_state.max_turns:
            st.session_state.interview_active = False
            with st.spinner("Generating final coach report..."):
                report = get_final_feedback(role, focus, st.session_state.messages, st.session_state.evaluations)
                st.session_state.messages.append({"role": "assistant", "content": report})
            
            # Display final report immediately
            with st.chat_message("assistant"):
                st.markdown(report)
                st.success("Interview Complete! Check your feedback above.")
        
        # 4. If not over, generate next question
        else:
            with st.spinner("Generating next question..."):
                next_q = get_next_question(role, resume, focus, st.session_state.messages, eval_data)
                st.session_state.messages.append({"role": "assistant", "content": next_q})
            
            with st.chat_message("assistant"):
                st.markdown(next_q)

elif not st.session_state.messages:
    st.info("👈 Fill out your profile in the sidebar and click 'Start Interview' to begin.")