import streamlit as st
import subprocess
import os
import datetime
from pathlib import Path
from core.reporting.empire_stats import empire_stats

st.set_page_config(page_title="GemForge Empire Dashboard", page_icon="🏰", layout="wide")

# Custom CSS for that "Dark Factory" feel
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #e0e0e0;
    }
    .stButton>button {
        border-radius: 5px;
        height: 3em;
        width: 100%;
    }
    .reportview-container .main .block-container {
        padding-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

st.title("🏰 GemForge Empire Dashboard")
st.caption("v2.0 — The Dark Factory Command Center")

# --- TOP LEVEL METRICS ---
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Gems Forged", empire_stats.get_project_count())
with col2:
    total_cost = empire_stats.get_total_costs()
    st.metric("Total Investment", f"${total_cost:.4f}")
with col3:
    weaver_stats = empire_stats.get_weaver_stats()
    st.metric("Lessons Learned", weaver_stats["total_lessons"])
with col4:
    st.metric("Empire Status", "Active", "Optimal")

# --- MAIN NAVIGATION ---
tabs = st.tabs(["🚀 Forge Control", "📦 Project Fleet", "🐝 Dynamic Swarm", "🕸️ The Weaver's Mind", "📊 Analytics"])

with tabs[0]:
    st.subheader("Launch New Mission")
    
    col_idea_input, col_oracle = st.columns([3, 1])
    
    with col_oracle:
        if st.button("🔮 Ask The Oracle"):
            st.info("Consulting the patterns...")
            # We can run the oracle directly or via CLI
            # For simplicity in Streamlit, let's run the logic directly
            from core.prediction.oracle import oracle as live_oracle
            ideas = live_oracle.generate_predictions()
            if ideas:
                st.session_state['oracle_ideas'] = ideas
            else:
                st.error("The Oracle is silent.")
    
    with col_idea_input:
        idea_placeholder = st.empty()
        default_idea = ""
        if 'oracle_ideas' in st.session_state and st.session_state['oracle_ideas']:
            st.markdown("### 🔮 Suggested Gems:")
            for i, suggestion in enumerate(st.session_state['oracle_ideas']):
                if st.button(f"Copy: {suggestion['title']} ({suggestion['type']})", key=f"sugg_{i}"):
                    default_idea = suggestion['one_liner']
        
        idea = st.text_area(
            "Paste your raw idea here",
            value=default_idea,
            placeholder='e.g. "An ear training iOS app that teaches pitch direction with pure tones"',
            height=150,
        )
    
    if st.button("🚀 IGNITE FACTORY", type="primary", disabled=not idea.strip()):
        st.info("Initiating Forge sequence...")
        st.code(f'python gemforge_cli.py new "{idea.strip()}"', language="bash")
        st.markdown("**Instructions:** Copy the command above and execute it in your terminal. Use `resume.py` for approval gates.")

with tabs[1]:
    st.subheader("Your Product Fleet")
    projects = empire_stats.get_recent_projects(limit=20)
    if not projects:
        st.info("No gems forged yet.")
    else:
        for p in projects:
            with st.expander(f"💎 {p['name']}"):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.write(f"**Path:** `{p['path']}`")
                    st.write(f"**Forged on:** {datetime.datetime.fromtimestamp(p['created']).strftime('%Y-%m-%d %H:%M')}")
                with c2:
                    if p['has_xcode']:
                        if st.button("Open Xcode", key=f"xcode_{p['name']}"):
                            xcodeprojs = [f for f in os.listdir(p['path']) if f.endswith(".xcodeproj")]
                            subprocess.Popen(["open", os.path.join(p['path'], xcodeprojs[0])])
                    if st.button("Open Finder", key=f"finder_{p['name']}"):
                        subprocess.Popen(["open", p['path']])
                
                # --- PILLAR 2: REFINEMENT SURGERY ---
                st.divider()
                st.markdown("#### 🔧 Refinement Surgery")
                refinement_request = st.text_input("What should we improve?", placeholder="e.g. 'Add a dark mode toggle' or 'Fix the button spacing'", key=f"refine_input_{p['name']}")
                if st.button("🚀 PROPOSE SURGERY", key=f"refine_btn_{p['name']}", disabled=not refinement_request.strip()):
                    st.info(f"Surgery plan for {p['name']} prepared.")
                    st.code(f'python iterate.py "{p["name"]}" "{refinement_request.strip()}"', language="bash")
                    st.markdown("**Run this in your terminal** to apply the improvements autonomously.")

with tabs[2]:
    st.subheader("🐝 Dynamic Agent Swarm")
    st.caption("Spawn a temporary specialist agent for a niche mission.")
    
    projects_list = empire_stats.get_recent_projects(limit=50)
    project_names = [p['name'] for p in projects_list]
    
    selected_project = st.selectbox("Target Project", project_names)
    mission = st.text_area("Mission Description", placeholder="e.g. 'Implement a complex FFT algorithm for audio processing' or 'Refactor the authentication flow to use OAuth 2.0'")
    
    if st.button("🚀 SPAWN SPECIALIST", type="primary", disabled=not mission.strip()):
        st.info(f"Swarm Protocol Initiated for {selected_project}...")
        st.code(f'python spawn_agent.py "{selected_project}" "{mission.strip()}"', language="bash")
        st.markdown("**Instructions:** Run this command to spawn and deploy the specialist agent.")

with tabs[3]:
    st.subheader("Self-Evolution & Memory")
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.markdown("### 🧠 User Taste Memory")
        st.write("**Core Values:**")
        for val in weaver_stats["core_values"]:
            st.markdown(f"- {val}")
        
        st.write("**Tech Preferences:**")
        st.json(weaver_stats["tech_prefs"])
        
    with col_b:
        st.markdown("### 📜 Recent Lessons")
        for l in weaver_stats["recent_lessons"]:
            # Lesson: (id, gem_id, ts, category, lesson, impact, related_agents, source, metadata)
            with st.container():
                st.markdown(f"**{l[3].upper()}** (Impact: {l[5]}/10)")
                st.write(l[4])
                st.caption(f"From {l[1]} at {l[2]}")
                st.divider()

with tabs[4]:
    st.subheader("Empire Analytics")
    st.info("Analytics engine coming soon in v2.1")
    st.progress(0.4)
