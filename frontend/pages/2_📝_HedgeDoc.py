import streamlit as st
import requests
import os
import sys

# Add parent directory to path to import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import API_URL

st.set_page_config(page_title="HedgeDoc Integration", layout="wide")

st.header("📝 HedgeDoc Integration")

with st.expander("Settings", expanded=True):
    base_url = st.text_input("HedgeDoc Base URL", value="https://demo.hedgedoc.org")
    cookie = st.text_input("Session Cookie (connect.sid)", type="password", help="Login to HedgeDoc, open DevTools -> Application -> Cookies, copy connect.sid value")

if st.button("List My Notes"):
    if not cookie:
        st.warning("Please enter a session cookie to see your history.")
    else:
        with st.spinner("Fetching History..."):
            try:
                resp = requests.post(f"{API_URL}/hedgedoc/history", json={"base_url": base_url, "cookie": f"connect.sid={cookie}" if "connect.sid" not in cookie else cookie})
                if resp.status_code == 200:
                    history = resp.json().get("history", [])
                    st.session_state['hd_history'] = history
                    st.success(f"Found {len(history)} notes.")
                else:
                    st.error(f"Error: {resp.text}")
            except Exception as e:
                st.error(f"Error connecting to backend: {e}")

if 'hd_history' in st.session_state:
    st.subheader("My Notes")
    
    # Bulk Download Section
    if st.session_state['hd_history']:
        # Create a form or just a container for the selection
        selected_notes = []
        
        col_ctrl1, col_ctrl2 = st.columns([4, 1.5])
        
        # Callback for Select All
        def toggle_select_all():
            new_state = st.session_state.get('select_all_chk', False)
            for note in st.session_state['hd_history']:
                st.session_state[f"chk_{note.get('id')}"] = new_state

        with col_ctrl1:
             st.checkbox("Select All", key="select_all_chk", on_change=toggle_select_all)

        with col_ctrl2:
             if st.button("Save Selected to Library"):
                 # We need to collect the states. Since checkboxes are unique keys, we can look them up.
                 # But standard Streamlit checkboxes don't return a list easily without a form or callback.
                 # We'll iterate the history and check session_state.
                 
                 count = 0
                 progress_bar = st.progress(0)
                 status_text = st.empty()
                 
                 notes_to_download = [
                     n for n in st.session_state['hd_history'] 
                     if st.session_state.get(f"chk_{n.get('id')}", False)
                 ]
                 
                 total = len(notes_to_download)
                 if total == 0:
                     st.warning("No notes selected.")
                 else:
                     for i, note in enumerate(notes_to_download):
                         status_text.text(f"Saving {i+1}/{total}: {note.get('text', 'Untitled')}...")
                         
                         note_url = f"{base_url}/{note.get('id')}"
                         safe_title = "".join(x for x in note.get('text', 'note') if x.isalnum() or x in "._- ")
                         filename = f"{safe_title}.md"
                         
                         try:
                             resp = requests.post(f"{API_URL}/hedgedoc/download", json={
                                 "url": note_url,
                                 "cookie": f"connect.sid={cookie}" if cookie and "connect.sid" not in cookie else cookie,
                                 "filename": filename
                             })
                             if resp.status_code == 200:
                                 count += 1
                         except Exception as e:
                             st.error(f"Error saving {filename}: {e}")
                             
                         progress_bar.progress((i + 1) / total)
                         
                     status_text.text(f"Done! Saved {count} notes to Library.")
                     st.success(f"Successfully saved {count} out of {total} notes to Library.")

    # Header for the table
    hcol0, hcol1, hcol2 = st.columns([0.5, 4, 1.5])
    hcol0.markdown("**Select**")
    hcol1.markdown("**Title**")
    hcol2.markdown("**Actions**")

    for note in st.session_state['hd_history']:
        col0, col1, col2 = st.columns([0.5, 4, 1.5])
        
        # Checkbox
        with col0:
            st.checkbox("", key=f"chk_{note.get('id')}")
            
        with col1:
            st.write(f"**{note.get('text', 'Untitled')}** (Last visited: {note.get('time', 'N/A')})")
            
        with col2:
            c1, c2 = st.columns(2)
            with c1:
                if st.button("View", key=f"view_{note.get('id')}"):
                    # View content
                    note_url = f"{base_url}/{note.get('id')}"
                    with st.spinner("Fetching Content..."):
                        try:
                            # Pass cookie for content too
                            c_resp = requests.post(f"{API_URL}/hedgedoc", json={
                                "url": note_url, 
                                "cookie": f"connect.sid={cookie}" if cookie and "connect.sid" not in cookie else cookie
                            })
                            if c_resp.status_code == 200:
                                st.session_state['hd_content'] = c_resp.json().get("content")
                                st.session_state['hd_current_note'] = note.get('text', 'Untitled')
                            else:
                                st.error(f"Error fetching content: {c_resp.text}")
                        except Exception as e:
                            st.error(f"Error: {e}")
            
            with c2:
                # Save button
                if st.button("Save", key=f"save_{note.get('id')}"):
                    note_url = f"{base_url}/{note.get('id')}"
                    # Default filename
                    safe_title = "".join(x for x in note.get('text', 'note') if x.isalnum() or x in "._- ")
                    filename = f"{safe_title}.md"
                    
                    with st.spinner(f"Saving as {filename}..."):
                        try:
                            resp = requests.post(f"{API_URL}/hedgedoc/download", json={
                                "url": note_url,
                                "cookie": f"connect.sid={cookie}" if cookie and "connect.sid" not in cookie else cookie,
                                "filename": filename
                            })
                            if resp.status_code == 200:
                                st.success(f"Saved to {resp.json().get('path')}")
                            else:
                                st.error(f"Error saving: {resp.text}")
                        except Exception as e:
                            st.error(f"Error: {e}")
                        
if 'hd_content' in st.session_state:
    st.markdown("---")
    st.subheader(f"Viewing: {st.session_state.get('hd_current_note', 'Note')}")
    st.markdown(st.session_state['hd_content'])


st.markdown("---")
st.subheader("Quick Fetch by URL")
url = st.text_input("Enter HedgeDoc URL", placeholder="https://demo.hedgedoc.org/...")

if url:
    col_q1, col_q2 = st.columns([1, 1])
    with col_q1:
        if st.button("Fetch HedgeDoc URL"):
            with st.spinner("Fetching..."):
                try:
                    # Optional cookie usage here too if user entered it
                    payload = {"url": url}
                    if cookie:
                        payload["cookie"] = f"connect.sid={cookie}" if "connect.sid" not in cookie else cookie
                            
                    resp = requests.post(f"{API_URL}/hedgedoc", json=payload)
                    if resp.status_code == 200:
                        content = resp.json().get("content")
                        st.markdown("### Preview")
                        st.markdown(content)
                    else:
                        st.error(f"Error fetching document: {resp.text}")
                except Exception as e:
                    st.error(f"Error: {e}")
    
    with col_q2:
        save_name = st.text_input("Filename to save as", value="hedgedoc_note.md")
        if st.button("Save to Server"):
            with st.spinner("Saving..."):
                try:
                    payload = {
                        "url": url, 
                        "filename": save_name
                    }
                    if cookie:
                        payload["cookie"] = f"connect.sid={cookie}" if "connect.sid" not in cookie else cookie
                    
                    resp = requests.post(f"{API_URL}/hedgedoc/download", json=payload)
                    if resp.status_code == 200:
                        st.success(f"Saved to {resp.json().get('path')}")
                    else:
                        st.error(f"Error saving: {resp.text}")
                except Exception as e:
                    st.error(f"Error: {e}")
