import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
