import streamlit as st
import requests
import os

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Summa", layout="wide")

st.title("📚 Summa")

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Local Files", "HedgeDoc", "GitHub Stats"])

if page == "Local Files":
    st.header("📂 Local Files")
    try:
        response = requests.get(f"{API_URL}/files")
        if response.status_code == 200:
            files = response.json()
            
            # --- Fetch Tags for Filtering & Management ---
            all_tags = []
            try:
                tags_resp = requests.get(f"{API_URL}/tags")
                if tags_resp.status_code == 200:
                    all_tags = tags_resp.json()
                else:
                    st.error("Could not fetch tags")
            except Exception as e:
                st.error(f"Error fetching tags: {e}")

            # --- Tag Filter ---
            selected_filter_tags = []
            if all_tags:
                selected_filter_tags = st.pills("Filter by Tags", options=all_tags, selection_mode="multi")
            
            # Filter files based on selection
            if selected_filter_tags:
                filtered_files = []
                for f in files:
                    file_tags = f.get('tags', [])
                    # Check overlap (OR logic: if file has ANY of the selected tags)
                    if any(t in selected_filter_tags for t in file_tags):
                        filtered_files.append(f)
                files = filtered_files
            
            # --- Tag Management ---
            with st.expander("Manage Tags"):
                st.subheader("Available Tags")
                # all_tags is already fetched above
                
                # Create new tag
                c1, c2 = st.columns([3, 1])
                with c1:
                    new_tag = st.text_input("New Tag Name")
                with c2:
                    if st.button("Add Tag"):
                        if new_tag:
                            requests.post(f"{API_URL}/tags", json={"name": new_tag})
                            st.rerun()
                
                # List and delete tags
                st.write("Existing Tags:")
                for t in all_tags:
                    col_t1, col_t2 = st.columns([4, 1])
                    with col_t1:
                        st.code(t)
                    with col_t2:
                        if st.button("🗑️", key=f"del_tag_{t}"):
                            requests.delete(f"{API_URL}/tags/{t}")
                            st.rerun()

            # File Uploader
            with st.expander("Upload New File"):
                uploaded_file = st.file_uploader("Choose a file", type=['md', 'txt', 'pdf', 'docx', 'pptx'])
                if uploaded_file is not None:
                    if st.button("Upload"):
                        with st.spinner("Uploading..."):
                            try:
                                files_up = {'file': (uploaded_file.name, uploaded_file, uploaded_file.type)}
                                up_resp = requests.post(f"{API_URL}/files/upload", files=files_up)
                                if up_resp.status_code == 200:
                                    st.success(f"Uploaded {uploaded_file.name}")
                                    st.rerun()
                                else:
                                    st.error(f"Upload failed: {up_resp.text}")
                            except Exception as e:
                                st.error(f"Error uploading: {e}")

            if files:
                # Group by folder maybe? or just list
                # For now, simple list
                for file_data in files:
                    with st.expander(f"{file_data['name']} ({file_data['path']})"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Type:** {file_data['type']}")
                            size_kb = file_data['size'] / 1024
                            st.write(f"**Size:** {size_kb:.2f} KB")
                        with col2:
                            st.write(f"**Modified:** {file_data.get('modified', 'N/A')}")
                        
                        # Tags Section
                        # Ensure all_tags is available (it should be from Manage Tags section)
                        # We use st.multiselect for editing
                        current_tags = file_data.get('tags', [])
                        # Filter current_tags to ensure they exist in all_tags (optional, but good for UI consistency if tags were deleted)
                        valid_current = [t for t in current_tags if t in all_tags]
                        # If a tag is assigned but not in all_tags (e.g. deleted), we might want to show it or not. 
                        # st.multiselect will error if default contains items not in options.
                        # So we unite them or filter. Lets unite.
                        # Actually if we want to allow users to see "deleted" tags on files, we should add them to options.
                        # But for now, let's just use valid_current to avoid errors.
                        
                        selected_tags = st.multiselect("Tags", options=all_tags, default=valid_current, key=f"tags_{file_data['path']}")
                        if st.button("Save Tags", key=f"mtag_{file_data['path']}"):
                             requests.post(f"{API_URL}/files/tags", json={"path": file_data["path"], "tags": selected_tags})
                             st.success("Tags saved")
                             st.rerun()

                        # Suggest Tags Button
                        if st.button("✨ Suggest Tags", key=f"suggest_{file_data['path']}"):
                             with st.spinner("Asking AI for tags..."):
                                 try:
                                     s_resp = requests.post(f"{API_URL}/files/suggest_tags", json={"path": file_data["path"]})
                                     if s_resp.status_code == 200:
                                         suggestions = s_resp.json().get("tags", [])
                                         st.session_state[f"suggestions_{file_data['path']}"] = suggestions
                                     else:
                                         st.error(f"Error: {s_resp.text}")
                                 except Exception as e:
                                     st.error(f"Error: {e}")

                        # Display suggestions if they exist in session state
                        if f"suggestions_{file_data['path']}" in st.session_state:
                            suggestions = st.session_state[f"suggestions_{file_data['path']}"]
                            if suggestions:
                                st.info(f"Suggested: {', '.join(suggestions)}")
                                if st.button("Apply Suggestions", key=f"apply_{file_data['path']}"):
                                     # Merge with current
                                     new_tags = list(set(current_tags + suggestions))
                                     u_resp = requests.post(f"{API_URL}/files/tags", json={"path": file_data["path"], "tags": new_tags})
                                     if u_resp.status_code == 200:
                                          st.success("Suggestions applied!")
                                          # Clear suggestions after applying
                                          del st.session_state[f"suggestions_{file_data['path']}"]
                                          st.rerun()
                                     else:
                                          st.error(f"Failed to apply tags: {u_resp.text}")
                            else:
                                st.warning("No suggestions generated.")
                                if st.button("Clear", key=f"clear_sugg_{file_data['path']}"):
                                    del st.session_state[f"suggestions_{file_data['path']}"]
                                    st.rerun()
                        
                        if st.button(f"View Content {file_data['name']}", key=file_data['path']):
                             # Fetch content
                             content_resp = requests.get(f"{API_URL}/files/content", params={"path": file_data["path"]})
                             if content_resp.status_code == 200:
                                 c_data = content_resp.json()
                                 if c_data.get("type") == "text":
                                     st.markdown(c_data.get("content"))
                                 else:
                                     st.info("This file type content cannot be displayed directly.")
                             else:
                                 st.error("Could not fetch content.")
                        
                        # Summary Section
                        st.markdown("---")
                        st.subheader("Summary")
                        
                        # 1. Try to fetch existing summary
                        summary_resp = requests.get(f"{API_URL}/files/summary", params={"path": file_data["path"]})
                        if summary_resp.status_code == 200:
                            summary_data = summary_resp.json()
                            st.write(summary_data.get("summary_text", "No summary text."))
                            st.caption(f"Generated at: {summary_data.get('generated_at')} by {summary_data.get('model_used')}")
                        else:
                            st.write("No summary available yet.")
                        
                        # 2. Generate button
                        if st.button(f"Generate Summary {file_data['name']}", key=f"gen_{file_data['path']}"):
                             st.write("Generating summary...")
                             try:
                                 # Request with stream=True
                                 gen_resp = requests.post(f"{API_URL}/files/summary", json={"path": file_data["path"]}, stream=True)
                                 
                                 if gen_resp.status_code == 200:
                                     # Streamlit's write_stream consumes a generator
                                     st.write_stream(gen_resp.iter_content(chunk_size=1024, decode_unicode=True))
                                     st.success("Summary generated!")
                                     
                                     # Optional: Rerun is tricky here because it might reload and show the "saved" summary immediately,
                                     # or user might want to see the stream finish first.
                                     if st.button("Refresh to see saved status"):
                                         st.rerun()
                                 else:
                                     st.error(f"Failed to generate: {gen_resp.text}")
                             except Exception as e:
                                 st.error(f"Error: {e}")
            else:
                st.info("No files found in the data directory. Add some files to 'data/' folder.")
        else:
            st.error(f"Failed to connect to backend: {response.status_code}")
    except requests.exceptions.ConnectionError as e:
        st.error(f"Backend is not running. Please start the FastAPI backend: {e}")

elif page == "HedgeDoc":
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
        for note in st.session_state['hd_history']:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"**{note.get('text', 'Untitled')}** (Last visited: {note.get('time', 'N/A')})")
            with col2:
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


            
elif page == "GitHub Stats":
    st.header("🐙 GitHub Contributions")
    username = st.text_input("Enter GitHub Username", placeholder="octocat")
    
    if username:
        if st.button("Fetch Stats"):
            with st.spinner("Fetching Github Data..."):
                try:
                    resp = requests.get(f"{API_URL}/github/{username}")
                    if resp.status_code == 200:
                        data = resp.json()
                        st.success(f"Found {data.get('raw_count')} recent events")
                        
                        st.subheader("Recent Activity")
                        for event in data.get("events", []):
                            st.write(f"- {event}")
                    else:
                        st.error("Could not fetch user data. Check username.")
                except Exception as e:
                    st.error(f"Error: {e}")

st.sidebar.markdown("---")
st.sidebar.info("Microservice PoC\nBackend: FastAPI\nFrontend: Streamlit")
