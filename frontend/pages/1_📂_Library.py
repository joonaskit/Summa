import streamlit as st
import requests
import os
import sys

# Add parent directory to path to import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import API_URL

@st.dialog("Confirm Deletion")
def confirm_delete(file_path, file_name):
    st.write(f"Are you sure you want to delete **{file_name}**?")
    st.warning("This action cannot be undone.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Cancel"):
            st.rerun()
    with col2:
        if st.button("Delete", type="primary"):
            try:
                # Use query param for consistency with backend
                resp = requests.delete(f"{API_URL}/files/delete", params={"path": file_path})
                if resp.status_code == 200:
                    st.success("Deleted successfully!")
                    st.rerun()
                else:
                    st.error(f"Failed to delete: {resp.text}")
            except Exception as e:
                st.error(f"Error: {e}")

def apply_suggestion_callback(file_path, current_tags, suggestions):
    new_tags = list(set(current_tags + suggestions))
    try:
        u_resp = requests.post(f"{API_URL}/files/tags", json={"path": file_path, "tags": new_tags})
        if u_resp.status_code == 200:
            # Update the multiselect state
            st.session_state[f"tags_{file_path}"] = new_tags
            # clear suggestions
            if f"suggestions_{file_path}" in st.session_state:
                del st.session_state[f"suggestions_{file_path}"]
            st.toast("Suggestions applied successfully!")
        else:
            st.toast(f"Failed to apply tags: {u_resp.text}")
    except Exception as e:
        st.toast(f"Error applying tags: {e}")

st.set_page_config(page_title="Library", layout="wide")

st.header("📂 Library")
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

        # --- Filters ---
        with st.expander("Filters", expanded=True):
            # Toggle Hidden Files
            show_hidden = st.checkbox("Show hidden files", value=False)
            if not show_hidden:
                files = [f for f in files if not f['name'].startswith('.')]
            
            # Row 1: Tags
            selected_filter_tags = []
            if all_tags:
                selected_filter_tags = st.pills("Tags", options=all_tags, selection_mode="multi", key="filter_tags")
            
            # Row 2: Type and Summary
            c_f1, c_f2 = st.columns(2)
            with c_f1:
                # Recalculate types based on potentially hidden-filtered files
                all_types = sorted(list(set(f.get('type', 'unknown') for f in files))) if files else []
                selected_types = st.pills("Document Type", options=all_types, selection_mode="multi", key="filter_types")
            
            with c_f2:
                summary_filter = st.pills("Summary Status", options=["All", "With Summary", "No Summary"], default="All", selection_mode="single", key="filter_summary")
        
        # Apply Filters
        filtered_files = files
        
        # 1. Tags
        if selected_filter_tags:
            filtered_files = [
                f for f in filtered_files 
                if any(t in selected_filter_tags for t in f.get('tags', []))
            ]
        
        # 2. Types
        if selected_types:
            filtered_files = [f for f in filtered_files if f.get('type') in selected_types]
            
        # 3. Summary
        if summary_filter == "With Summary":
            filtered_files = [f for f in filtered_files if f.get('has_summary')]
        elif summary_filter == "No Summary":
            filtered_files = [f for f in filtered_files if not f.get('has_summary')]
        
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
        # File Uploader
        with st.expander("Upload New File(s)"):
            # Initialize session state for uploader reset
            if "uploader_key" not in st.session_state:
                st.session_state["uploader_key"] = 0

            # Display success message from previous run if enabled
            if "upload_success_msg" in st.session_state:
                st.success(st.session_state["upload_success_msg"])
                del st.session_state["upload_success_msg"]

            # Use dynamic key to allow resetting
            uploaded_files = st.file_uploader(
                "Choose files or drag a folder", 
                type=['md', 'txt', 'pdf', 'docx', 'pptx'], 
                accept_multiple_files=True,
                key=f"uploader_{st.session_state['uploader_key']}"
            )

            if uploaded_files:
                if st.button("Upload All"):
                    success_count = 0
                    failed_count = 0
                    total = len(uploaded_files)
                    
                    progress_bar = st.progress(0)
                    
                    for i, uploaded_file in enumerate(uploaded_files):
                        try:
                            # Update progress
                            progress_bar.progress((i) / total, text=f"Uploading {uploaded_file.name}...")
                            
                            files_up = {'file': (uploaded_file.name, uploaded_file, uploaded_file.type)}
                            up_resp = requests.post(f"{API_URL}/files/upload", files=files_up)
                            if up_resp.status_code == 200:
                                success_count += 1
                            else:
                                failed_count += 1
                                st.error(f"Upload failed for {uploaded_file.name}: {up_resp.text}")
                        except Exception as e:
                            failed_count += 1
                            st.error(f"Error uploading {uploaded_file.name}: {e}")
                            
                    progress_bar.progress(1.0, text="Done!")
                    
                    if success_count > 0:
                        # Update session state to reset uploader and show message
                        st.session_state["uploader_key"] += 1
                        st.session_state["upload_success_msg"] = f"Successfully uploaded {success_count} files."
                        
                    if failed_count > 0:
                        st.warning(f"Failed to upload {failed_count} files.")
                        
                    if success_count > 0:
                        st.rerun()

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
                        c2_1, c2_2 = st.columns([3, 1])
                        with c2_1:
                            st.write(f"**Modified:** {file_data.get('modified', 'N/A')}")
                        with c2_2:
                            if st.button("🗑️", key=f"del_{file_data['path']}", help="Delete File", type="primary"):
                                confirm_delete(file_data['path'], file_data['name'])
                    
                    # Tags Section
                    # Ensure all_tags is available (it should be from Manage Tags section)
                    # We use st.multiselect for editing
                    current_tags = file_data.get('tags', [])
                    # Filter current_tags to ensure they exist in all_tags (optional, but good for UI consistency if tags were deleted)
                    valid_current = [t for t in current_tags if t in all_tags]
                    
                    tag_key = f"tags_{file_data['path']}"
                    if tag_key not in st.session_state:
                        st.session_state[tag_key] = valid_current
                        
                    selected_tags = st.multiselect("Tags", options=all_tags, key=tag_key)
                    if st.button("Save Tags", key=f"mtag_{file_data['path']}"):
                        requests.post(f"{API_URL}/files/tags", json={"path": file_data["path"], "tags": selected_tags})
                        st.success("Tags saved")
                        st.rerun()

                    # Suggest Tags Button
                    if st.button("✨ Suggest Tags", key=f"suggest_{file_data['path']}"):
                        st.write(f"DEBUG: {file_data['path']}")
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
                            st.button(
                                "Apply Suggestions", 
                                key=f"apply_{file_data['path']}",
                                on_click=apply_suggestion_callback,
                                args=(file_data['path'], current_tags, suggestions)
                            )
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
