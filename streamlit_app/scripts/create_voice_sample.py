import os
import json
from database.database import SessionLocal
from database.models import User, Dataset, AudioFile, Annotation
from database.enums import UserRole, AudioStatus
import uuid

def seed_voice_data():
    db = SessionLocal()
    
    # 1. Get annotator
    annotator = db.query(User).filter(User.username == "annotator1").first()
    if not annotator:
        print("Annotator not found!")
        return
        
    # 2. Get Dataset
    dataset = db.query(Dataset).filter(Dataset.name == "Sample Dataset").first()
    
    # 3. Create Audio File
    audio_path = os.path.join(os.getcwd(), "assets", "audio", "voice_sample.wav")
    
    # The actual duration is about 18 seconds (let's set it dynamically or just hardcode ~18s)
    # Using python's wave module to get exact duration
    import wave
    try:
        with wave.open(audio_path, 'r') as f:
            frames = f.getnframes()
            rate = f.getframerate()
            duration = frames / float(rate)
    except:
        duration = 18.0

    audio = AudioFile(
        dataset_id=dataset.id,
        filename="voice_sample.wav",
        original_filename="voice_sample.wav",
        file_path=audio_path,
        language="English",
        duration=duration,
        status=AudioStatus.ASSIGNED,
        uploaded_by=annotator.id,
        assigned_to=annotator.id
    )
    db.add(audio)
    db.commit()
    db.refresh(audio)
    print("Assigned voice sample task to annotator1")

    # 4. Create an Annotation with pre-filled segments
    segments = [
        {
            "id": 1,
            "start": 0.0,
            "end": 3.0,
            "speaker": "Speaker 0 (Female)",
            "text": "Hello there. This is a sample audio file featuring spoken words."
        },
        {
            "id": 2,
            "start": 3.0,
            "end": 7.5,
            "speaker": "Speaker 0 (Female)",
            "text": "We are generating this audio so that you can test the annotation platform with realistic voice data."
        },
        {
            "id": 3,
            "start": 7.5,
            "end": 14.5,
            "speaker": "Speaker 0 (Female)",
            "text": "The transcript will contain these exact words, broken down into segments, allowing you to test the synchronization between the audio waveform and the text editor."
        },
        {
            "id": 4,
            "start": 14.5,
            "end": duration,
            "speaker": "Speaker 0 (Female)",
            "text": "Thank you for testing."
        }
    ]

    annotation = Annotation(
        audio_id=audio.id,
        annotator_id=annotator.id,
        transcript=json.dumps(segments),
        rsml_content=""
    )
    db.add(annotation)
    db.commit()
    print("Created annotation with segments")

    db.close()

if __name__ == "__main__":
    seed_voice_data()
