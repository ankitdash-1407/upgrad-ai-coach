import os
import json
from groq import Groq
from tenacity import retry, wait_exponential, stop_after_attempt
from dotenv import load_dotenv

load_dotenv()

# Initialize the Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def load_prompt(filename: str) -> str:
    with open(os.path.join("prompts", filename), "r", encoding="utf-8") as f:
        return f.read()

@retry(wait=wait_exponential(multiplier=2, min=2, max=10), stop=stop_after_attempt(3))
def get_next_question(role: str, resume: str, focus: str, chat_history: list, last_eval: dict = None) -> str:
    """Agent 1: The Interviewer"""
    system_prompt = load_prompt("interviewer.txt").format(role=role, resume=resume, focus=focus)
    
    messages = [{"role": "system", "content": system_prompt}]
    
    if last_eval:
        messages.append({
            "role": "system", 
            "content": f"[SYSTEM NOTE - PREVIOUS EVALUATION]: {json.dumps(last_eval)}\nAdjust your next question's difficulty based on this."
        })
    
    for msg in chat_history:
        messages.append({"role": msg["role"], "content": msg["content"]})
        
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile", # Groq's newest, smartest model
        messages=messages,
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

@retry(wait=wait_exponential(multiplier=2, min=2, max=10), stop=stop_after_attempt(3))
def evaluate_turn(role: str, question: str, answer: str) -> dict:
    """Agent 2: The Silent Evaluator"""
    system_prompt = load_prompt("evaluator.txt").format(role=role, question=question, answer=answer)
    
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant", # Lightning fast model for background tasks
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Analyze my answer and output the JSON evaluation."}
            ],
            response_format={"type": "json_object"}, # Strict JSON mode
            temperature=0
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        # Fallback to prevent UI crashes if JSON parsing fails
        return {
            "turn_score": 5, "technical_depth_score": 5, "communication_score": 5,
            "difficulty_recommendation": "maintain", "detected_behavior": "error",
            "key_gap": "Parse failed", "key_strength": "N/A"
        }

@retry(wait=wait_exponential(multiplier=2, min=2, max=10), stop=stop_after_attempt(3))
def get_final_feedback(role: str, focus: str, chat_history: list, eval_history: list) -> str:
    """Agent 3: The Coach"""
    transcript = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
    system_prompt = load_prompt("coach.txt").format(
        role=role, 
        focus=focus, 
        evaluation_history=json.dumps(eval_history, indent=2), 
        transcript=transcript
    )
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "The interview is over. Generate the final Markdown report."}
        ],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()