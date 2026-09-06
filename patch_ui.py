import re

with open('app/ui.py', 'r', encoding='utf-8') as f:
    content = f.read()

import_time = "import time\n"
if "import time" not in content:
    content = content.replace("import streamlit as st", "import streamlit as st\nimport time")

old_storyboard = '''        if st.button("Generate Storyboard (Mock)"):
            with st.spinner("Generating Image Prompts..."):
                headers = {"Authorization": f"Bearer {token_data['token']['id_token']}"}
                payload = {"session_id": st.session_state.session_id or "demo", "scene_query": "Opening Scene"}
                res = requests.post(f"{API_BASE_URL}/tools/producers/storyboard", json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    st.write(f"**Prompt:** {data.get('image_prompt')}")
                    if data.get("image_base64"):
                        import base64
                        st.image(base64.b64decode(data["image_base64"]))
                    else:
                        st.json(data)
                else:
                    st.error("Error calling endpoint")'''

new_storyboard = '''        st.subheader("Batch Storyboard Generation")
        if "available_scenes" not in st.session_state:
            st.session_state.available_scenes = []
            
        if st.button("Load Scenes"):
            with st.spinner("Extracting scenes..."):
                headers = {"Authorization": f"Bearer {token_data['token']['id_token']}"}
                sess_id = st.session_state.session_id or "demo"
                res = requests.get(f"{API_BASE_URL}/tools/producers/scenes?session_id={sess_id}", headers=headers)
                if res.status_code == 200:
                    st.session_state.available_scenes = res.json().get("scenes", [])
                    st.success(f"Found {len(st.session_state.available_scenes)} scenes.")
                else:
                    st.error("Failed to load scenes.")
                    
        if st.session_state.available_scenes:
            selected_scenes = st.multiselect("Select Scenes", st.session_state.available_scenes, default=st.session_state.available_scenes)
            
            if st.button("Generate Storyboards Document"):
                if not selected_scenes:
                    st.warning("Please select at least one scene.")
                else:
                    headers = {"Authorization": f"Bearer {token_data['token']['id_token']}"}
                    payload = {"session_id": st.session_state.session_id or "demo", "scenes": selected_scenes}
                    res = requests.post(f"{API_BASE_URL}/tools/producers/storyboard/batch", json=payload, headers=headers)
                    if res.status_code == 200:
                        task_id = res.json().get("task_id")
                        st.info("Task submitted! Generating in background...")
                        
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        while True:
                            status_res = requests.get(f"{API_BASE_URL}/tools/producers/storyboard/status/{task_id}", headers=headers)
                            if status_res.status_code == 200:
                                status_data = status_res.json()
                                stat = status_data.get("status")
                                prog = status_data.get("progress", 0)
                                total = status_data.get("total", len(selected_scenes))
                                
                                progress_val = prog / total if total > 0 else 0
                                progress_bar.progress(progress_val)
                                status_text.write(f"Status: {stat} ({prog}/{total})")
                                
                                if stat == "completed":
                                    url = status_data.get("url")
                                    st.success("Generation Complete!")
                                    st.markdown(f"[**Download Storyboard PDF here**]({url})")
                                    break
                                elif stat == "failed":
                                    st.error("Task failed.")
                                    break
                            time.sleep(2)
                    else:
                        st.error("Failed to submit batch generation task.")'''

content = content.replace(old_storyboard, new_storyboard)

with open('app/ui.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated ui.py")
