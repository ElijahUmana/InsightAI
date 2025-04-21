import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = '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'
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ASSEMBLYAI_TOKEN = os.getenv("ASSEMBLYAI_TOKEN")
MONGODB_URL = os.getenv("MONGODB_URL")
DB_NAME = os.getenv("DB_NAME")  
