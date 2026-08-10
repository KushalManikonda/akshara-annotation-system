import os
import json
import base64
import streamlit as st
import streamlit.components.v1 as components

# Declare the component
_RELEASE = False  # Set to False to develop using a local file

parent_dir = os.path.dirname(os.path.abspath(__file__))
build_dir = os.path.join(parent_dir, "wavesurfer_custom")
_wavesurfer_component = components.declare_component("wavesurfer_editor", path=build_dir)


def render(task, annotation, is_read_only=False):
    """
    Renders the custom Wavesurfer + RSML Editor component.
    """
    # Create segments from RSML string (very basic parse for demo, or dummy if empty)
    # In a full app, this would use the RSMLParser to split by @speaker-start tags.
    # For now, if empty we just start with an empty segment array.
    
    # We need to serve the audio file to the JS component. 
    # Because it's a local file and we can't easily serve it directly in this Streamlit setup,
    # we convert it to a base64 data URI (assuming it's reasonably sized for testing).
    audio_path = task.file_path.replace('\\', '/')
    
    if os.path.exists(audio_path):
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
            b64 = base64.b64encode(audio_bytes).decode()
            ext = os.path.splitext(audio_path)[1][1:] or "mp3"
            audio_url = f"data:audio/{ext};base64,{b64}"
    else:
        st.warning(f"Audio file not found: {audio_path}")
        return None

    # Retrieve or parse segments
    # Ideally, we parse annotation.transcript to JSON. Here we try to parse it.
    segments = []
    if annotation.transcript:
        try:
            # If we store it as JSON string
            segments = json.loads(annotation.transcript)
        except:
            # Fallback if it's raw text
            segments = [{
                "id": 1,
                "start": 0,
                "end": 5,
                "speaker": "Speaker 0 (Female)",
                "text": annotation.transcript
            }]

    # Call the component
    result = _wavesurfer_component(
        audio_url=audio_url,
        segments=segments,
        task_id=task.id,
        key=f"ws_editor_{task.id}",
    )

    if result and isinstance(result, dict):
        if result.get("action") == "save":
            new_segments = result.get("segments", [])
            # In a real app we'd convert segments back to RSML text.
            # Here we just save the JSON string to annotation.transcript.
            from services.annotation_service import save_annotation
            from utils.logger import logger
            
            # Simple conversion to text (valid RSML speaker tags)
            import re
            rsml_text = ""
            for seg in new_segments:
                speaker_str = seg.get('speaker', '')
                text = seg.get('text', '')
                
                match = re.search(r'\d+', speaker_str)
                if match:
                    speaker_idx = int(match.group()) + 1
                else:
                    speaker_idx = 1
                    
                rsml_text += f"&s{speaker_idx}-start {text} &s{speaker_idx}-end\n\n"
                
            ok = save_annotation(annotation.id, json.dumps(new_segments), rsml_text.strip())
            if ok:
                logger.info(f"Auto-saved draft for annotation {annotation.id} from Wavesurfer")
                st.success("Draft saved successfully!")

    return result
