import wave
import struct
import math
import os
from database.database import SessionLocal
from database.models import User, Dataset, AudioFile, Annotation
from database.enums import UserRole, AudioStatus
import uuid

def generate_sample_audio(filename, duration_sec=30, sample_rate=44100, freq=440.0):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    obj = wave.open(filename, 'w')
    obj.setnchannels(1)
    obj.setsampwidth(2)
    obj.setframerate(sample_rate)

    for i in range(int(duration_sec * sample_rate)):
        value = int(32767.0 * math.sin(freq * math.pi * float(i) / float(sample_rate)))
        data = struct.pack('<h', value)
        obj.writeframesraw(data)
    obj.close()

def seed_data():
    db = SessionLocal()
    
    # 1. Get or create annotator
    annotator = db.query(User).filter(User.username == "annotator1").first()
    if not annotator:
        annotator = User(username="annotator1", email="anno1@test.com", password_hash="dummy", role=UserRole.ANNOTATOR)
        db.add(annotator)
        db.commit()
        db.refresh(annotator)
        print("Created annotator1 user")
        
    # 2. Create Dataset
    dataset = Dataset(
        name="Sample Dataset",
        zip_filename="sample.zip",
        language="English",
        uploaded_by=annotator.id,
        total_files=1,
        total_duration=30.0
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    
    # 3. Create Audio File
    audio_path = os.path.join(os.getcwd(), "assets", "audio", "sample_beep.wav")
    generate_sample_audio(audio_path, duration_sec=30)
    print(f"Generated sample audio at {audio_path}")
    
    audio = AudioFile(
        dataset_id=dataset.id,
        filename="sample_beep.wav",
        original_filename="sample_beep.wav",
        file_path=audio_path,
        language="English",
        duration=30.0,
        status=AudioStatus.ASSIGNED,
        uploaded_by=annotator.id,
        assigned_to=annotator.id
    )
    db.add(audio)
    db.commit()
    print("Assigned sample task to annotator1")
    
    db.close()

if __name__ == "__main__":
    seed_data()
