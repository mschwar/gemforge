import streamlit as st
import subprocess
import sys
import os

st.set_page_config(page_title="GemForge Dashboard", page_icon="⚒️", layout="centered")

st.title("⚒️ GemForge — AI Product Factory")
st.caption("Raw idea → complete runnable app")

st.divider()

idea = st.text_area(
    "Paste your raw idea here",
    placeholder='e.g. "An ear training iOS app that teaches pitch direction with pure tones"',
    height=100,
)

col1, col2 = st.columns([2, 1])

with col1:
    forge_btn = st.button("🚀 Forge this idea", type="primary", disabled=not idea.strip())

with col2:
    st.caption("Runs the full 13-agent factory")

if forge_btn and idea.strip():
    st.info("Launching GemForge factory...")
    st.code(f'python gemforge_cli.py new "{idea.strip()}"', language="bash")
    st.markdown("**Run the command above in your terminal, then:**")
    st.code("python resume.py approve", language="bash")

st.divider()

# Show recent projects
projects_root = os.path.expanduser("~/Documents/GitHub/gemforge-projects")
if os.path.isdir(projects_root):
    projects = sorted(
        [d for d in os.listdir(projects_root) if os.path.isdir(os.path.join(projects_root, d))],
        reverse=True,
    )
    if projects:
        st.subheader("Recent Projects")
        for proj in projects[:5]:
            proj_path = os.path.join(projects_root, proj)
            xcodeprojs = [f for f in os.listdir(proj_path) if f.endswith(".xcodeproj")]
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(f"**{proj}**")
                st.caption(proj_path)
            with col_b:
                if xcodeprojs:
                    if st.button("Open Xcode", key=proj):
                        subprocess.Popen(["open", os.path.join(proj_path, xcodeprojs[0])])
            st.divider()
    else:
        st.info("No projects yet — forge your first idea above!")
else:
    st.info("No projects yet — forge your first idea above!")
