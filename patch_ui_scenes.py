import re

with open('app/ui.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_producers = '''    with tab_producers:
        st.header("Filmmakers & Producers Tools")
        if st.button("Generate Script Breakdown (Mock)"):
            with st.spinner("Processing..."):
                headers = {"Authorization": f"Bearer {token_data['token']['id_token']}"}
                payload = {"session_id": st.session_state.session_id or "demo", "scene_query": "Act 1"}
                res = requests.post(f"{API_BASE_URL}/tools/producers/breakdown", json=payload, headers=headers)
                if res.status_code == 200:
                    st.json(res.json())
                else:
                    st.error("Error calling endpoint")
                    
        if st.button("Generate Storyboard (Mock)"):
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

new_producers = '''    with tab_producers:
        st.header("Filmmakers & Producers Tools")
        
        # Load scenes into session state if they aren't there
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
                    
        selected_scene = None
        if st.session_state.available_scenes:
            selected_scene = st.selectbox("Select a Scene", st.session_state.available_scenes)
            
        if selected_scene:
            if st.button("Generate Script Breakdown (Mock)"):
                with st.spinner("Processing..."):
                    headers = {"Authorization": f"Bearer {token_data['token']['id_token']}"}
                    payload = {"session_id": st.session_state.session_id or "demo", "scene_query": selected_scene}
                    res = requests.post(f"{API_BASE_URL}/tools/producers/breakdown", json=payload, headers=headers)
                    if res.status_code == 200:
                        st.json(res.json())
                    else:
                        st.error("Error calling endpoint")
                        
            if st.button("Generate Storyboard (Mock)"):
                with st.spinner("Generating Image Prompts..."):
                    headers = {"Authorization": f"Bearer {token_data['token']['id_token']}"}
                    payload = {"session_id": st.session_state.session_id or "demo", "scene_query": selected_scene}
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

if old_producers in content:
    content = content.replace(old_producers, new_producers)
    with open('app/ui.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched ui.py successfully")
else:
    print("Could not find the block to replace in ui.py")
