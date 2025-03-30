import streamlit as st
import google.generativeai as genai
from datetime import datetime
import pandas as pd
import os
import random
import time
import json
import html  # ✅ Added for escaping AI output
from dotenv import load_dotenv
from streamlit_lottie import st_lottie

# --- Load environment variables ---
load_dotenv()
IS_DEV = os.getenv("APP_MODE") == "dev"

# --- Load Lottie JSON from local file ---
def load_lottiefile(filepath: str):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

# --- Streamlit Page Config ---
st.set_page_config(page_title="Prompt Synthesizer", page_icon="🧠", layout="centered")

# --- Load API Key ---
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    st.error("❌ GOOGLE_API_KEY not found. Add it to .streamlit/secrets.toml.")
    st.stop()

# --- Configure Gemini ---
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("models/gemini-1.5-flash")

# --- Prompt Tips ---
tips = [
    "Keep prompts specific, not vague.",
    "Include sample inputs/outputs if you can.",
    "Ask the AI to adopt a role: 'Act like a teacher...'",
    "Use bullet points for structured tasks.",
    "Mention tone and audience clearly.",
    "Avoid multi-tasking prompts. Focus on one goal.",
    "Review and refine your prompt after the first try!"
]
random_tip = random.choice(tips)

# --- Load Prompt History (only in dev mode) ---
history_path = "prompt_history.csv"
if IS_DEV and os.path.exists(history_path):
    past_prompts = pd.read_csv(history_path)
else:
    past_prompts = pd.DataFrame()

# --- Valid tone options ---
valid_tones = [
    "Clear and helpful", "Professional", "Casual", "Funny", "Creative",
    "Motivational", "Witty", "Analytical", "Cynical but comforting", "Roasty",
    "Passive aggressive", "Aggressively encouraging", "Satirical", "Irritated",
    "Snarky", "Reflective"
]

# --- Template categories and emojis ---
templates_by_category = {
    "Real Estate": {
        "Cold Outreach Message": {
            "goal": "Craft a short, attention-grabbing message to reach out to a new commercial real estate prospect in Tucson, AZ.",
            "tone": "Professional",
            "output_type": "Text",
            "audience": "Commercial property owners"
        },
        "Market Summary Generator": {
            "goal": "Summarize the current real estate market trends for investors in a specific submarket.",
            "tone": "Clear and helpful",
            "output_type": "Markdown",
            "audience": "CRE investors"
        },
        "Deal Analysis Helper": {
            "goal": "Help analyze the pros and cons of an industrial property investment opportunity in Tucson, AZ.",
            "tone": "Analytical",
            "output_type": "Bullet List",
            "audience": "CRE analysts and brokers"
        }
    },
    "Productivity & Learning": {
        "Productivity Prompt Planner": {
            "goal": "Generate a set of focused prompts to help me plan and prioritize my day effectively.",
            "tone": "Motivational",
            "output_type": "Bullet List",
            "audience": "Busy professionals and productivity nerds"
        },
        "Prompt Engineering Optimizer": {
            "goal": "Take a rough prompt I've written and improve it so it's more structured, clear, and effective.",
            "tone": "Clear and helpful",
            "output_type": "Markdown",
            "audience": "Anyone learning how to prompt better"
        },
        "Weekly Review Wizard": {
            "goal": "Guide me through a weekly review of what I accomplished, learned, and what I want to focus on next.",
            "tone": "Reflective",
            "output_type": "Conversation",
            "audience": "Personal growth and productivity focused users"
        }
    },
    "Creative & Fun": {
        "Vibecode Brainstorm Buddy": {
            "goal": "Come up with fresh, creative app or automation ideas that I could build with my current skills.",
            "tone": "Creative",
            "output_type": "Bullet List",
            "audience": "A vibecoder looking for weekend build ideas"
        },
        "Mindset Reframe": {
            "goal": "Help me reframe a negative thought or frustration into something more constructive and empowering.",
            "tone": "Witty",
            "output_type": "Text",
            "audience": "Someone in a funk who needs a boost"
        },
        "Existential Crisis Coach": {
            "goal": "Help me cope with the crushing weight of late capitalism using sarcasm and dark humor.",
            "tone": "Cynical but comforting",
            "output_type": "Text",
            "audience": "Millennials spiraling at 2AM"
        },
        "Roast My Life Decisions": {
            "goal": "Make fun of me for buying a $7 latte instead of saving for retirement, but make it clever and a little too real.",
            "tone": "Roasty",
            "output_type": "Bullet List",
            "audience": "People who enjoy pain as comedy"
        },
        "Email Response Rage Filter": {
            "goal": "Help me respond to a deeply annoying email in a professional tone while screaming internally.",
            "tone": "Passive aggressive",
            "output_type": "Text",
            "audience": "Anyone who's ever replied all by accident"
        },
        "Clean Your Damn Room Bot": {
            "goal": "Write a motivational pep talk that uses tough love and light profanity to convince me to clean my disgusting room.",
            "tone": "Aggressively encouraging",
            "output_type": "Text",
            "audience": "Procrastinators and goblins"
        },
        "Startup Idea Generator (That Probably Sucks)": {
            "goal": "Give me absurd startup ideas that sound real until you think about them for more than 10 seconds.",
            "tone": "Satirical",
            "output_type": "Bullet List",
            "audience": "Tech bros with too much VC money"
        },
        "Rage Journal Prompt": {
            "goal": "Give me a writing prompt to vent all my rage about people who don’t use their turn signals.",
            "tone": "Irritated",
            "output_type": "Markdown",
            "audience": "Drivers barely holding on"
        },
        "Corporate Bullshit Translator": {
            "goal": "Take a vague corporate memo and rewrite it with brutal honesty, swearing allowed.",
            "tone": "Snarky",
            "output_type": "Text",
            "audience": "Employees who know the game"
        }
    }
}

category_emojis = {
    "Real Estate": "🏢",
    "Productivity & Learning": "📈",
    "Creative & Fun": "🎉"
}

# --- Flatten templates ---
templates = {}
template_categories = {}
for category, entries in templates_by_category.items():
    for name, data in entries.items():
        templates[name] = data
        template_categories[name] = category

# --- Hero Banner ---
st.markdown("""
    <div style="background: linear-gradient(135deg, #6e8efb, #a777e3); padding: 2rem 1rem; border-radius: 1.5rem; text-align: center; color: white; margin-bottom: 2rem;">
        <h1 style="font-size: 2.5rem;">💡 Prompt Synthesizer</h1>
        <p style="font-size: 1.1rem;">Turn your rough idea into a polished AI prompt</p>
    </div>
""", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    lottie_json = load_lottiefile("idea.json")
    st_lottie(lottie_json, width=200, height=200, key="idea")
    st.markdown("<h2>💡 Prompt Toolkit</h2>", unsafe_allow_html=True)
    st.markdown(f"📌 <i>Tip of the Day:</i> <small>{random_tip}</small>", unsafe_allow_html=True)
    st.markdown("---")
    if st.button("🎲 Surprise Me!"):
        st.session_state.selected_template = random.choice(list(templates.keys()))

st.sidebar.markdown("<h3>📁 Templates</h3>", unsafe_allow_html=True)
for category, entries in templates_by_category.items():
    emoji = category_emojis.get(category, "")
    st.sidebar.markdown(f"<h5>{emoji} {category}</h5>", unsafe_allow_html=True)
    for name in entries:
        if st.sidebar.button(name):
            st.session_state.selected_template = name

# --- Prompt Input Form ---
selected_template = st.session_state.get("selected_template", "")
template_data = templates.get(selected_template, {})
prefill = template_data if template_data else {}

with st.form("prompt_form"):
    st.markdown("### ✍️ Your Prompt Details")
    goal = st.text_area("💡 What do you want the AI to do?", value=prefill.get("goal", ""))
    col1, col2 = st.columns(2)
    with col1:
        tone = st.selectbox("🎭 Tone or vibe", valid_tones, index=valid_tones.index(prefill.get("tone", "Clear and helpful")))
    with col2:
        output_type = st.selectbox("🧾 Output format", ["Text", "Conversation", "Image Prompt", "Markdown", "Bullet List", "JSON"],
                                   index=["Text", "Conversation", "Image Prompt", "Markdown", "Bullet List", "JSON"].index(prefill.get("output_type", "Text")))
    audience = st.text_input("👥 Who's it for? (Optional)", value=prefill.get("audience", ""))
    save_txt = st.checkbox("💾 Save this to a .txt file?")
    submitted = st.form_submit_button("✨ Generate Prompt")

# --- Prompt Generation ---
if submitted:
    with st.spinner("🪄 Synthesizing your prompt..."):
        prompt_template = f"""
You are a professional AI prompt engineer. Your task is to turn a rough user idea into a clear, structured, and effective AI prompt.

Here is the input:
- Goal: {goal}
- Tone: {tone}
- Output Type: {output_type}
- Audience: {audience}

Write a full prompt that:
- Starts by instructing the AI what role to take
- Clearly sets the task
- Specifies the tone or style
- Includes formatting guidance (if helpful)
- Optionally includes a sample input/output pair
- Ends with a short tip on how to customize it further

Respond only with the generated prompt and tip.
"""
        try:
            response = model.generate_content(prompt_template)
            result = response.text
            escaped_result = html.escape(result)  # ✅ Prevent broken rendering

            st.markdown("## 🌟 Your Generated Prompt")
            st.markdown(f"""
                <div style='background-color: #fdfdfd; border-left: 5px solid #a777e3; border-radius: 0.5rem; padding: 1rem; font-family: monospace; font-size: 0.9rem; line-height: 1.6; white-space: pre-wrap; box-shadow: 0 4px 12px rgba(0,0,0,0.05);'>{escaped_result}</div>
            """, unsafe_allow_html=True)

            st.download_button("📥 Download Prompt", result, file_name="prompt.txt", mime="text/plain")

            if save_txt:
                filename = f"prompt_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(result)
                st.toast(f"💾 Saved to {filename}")

            new_row = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "goal": goal,
                "tone": tone,
                "output_type": output_type,
                "audience": audience,
                "prompt": result
            }

            if IS_DEV:
                if os.path.exists(history_path):
                    df = pd.read_csv(history_path)
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                else:
                    df = pd.DataFrame([new_row])
                df.to_csv(history_path, index=False)

        except Exception as e:
            st.error(f"⚠️ Something went wrong:\n\n{e}")

# --- Dev-only Prompt History ---
if IS_DEV and os.path.exists(history_path):
    st.markdown("## 🕰️ Prompt History")
    with st.expander("Click to view your saved prompts"):
        history_df = pd.read_csv(history_path)
        st.dataframe(history_df.style.set_properties(**{
            'text-align': 'left',
            'white-space': 'pre-wrap'
        }), use_container_width=True)

# --- Footer ---
sign_offs = [
    "Built by Ryan Martin. If it breaks, it's your fault.",
    "Another lovingly overengineered tool by Ryan Martin.",
    "If you're reading this, congrats. You're now tech support. - RM",
    "Ryan Martin made this. Don't encourage him."
]

st.markdown("""
    <style>
    .footer-note { text-align: center; font-size: 0.9rem; color: gray; }
    @media print {
        .footer-note { display: none; }
    }
    </style>
""", unsafe_allow_html=True)

with st.expander("👋 About this app"):
    st.markdown(f"""
    <div class="footer-note">
        {random.choice(sign_offs)}
    </div>
    """, unsafe_allow_html=True)
