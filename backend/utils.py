import config
import io
import wave
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import texttospeech
from pydub import AudioSegment
import json
import time
import mimetypes
import requests
import time
import os

APP_KEY = "3c9a7ad798ebeb8d5c6b74d30b902c38aa1c56cd1cc4d78f10cdc4ae4bbd88aa"
APP_ID = "insightai_c0fe0f_bf33f1"

def identify_learning_style_and_hobby(transcript):
    """
    Identify the learning style and hobby from the given transcript.
    Uses OpenAI API to extract this information based on the content of the transcript.
    """
    ENDPOINT = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
    }

    def make_api_call(messages):
        data = {
            "model": "gpt-4",   # Specify the model, adjust if necessary
            "messages": messages
        }
        response = requests.post(ENDPOINT, headers=headers, json=data)
        response_data = response.json()
        
        # Log the full API response for debugging
        print(response_data)

        if 'choices' in response_data:
            return response_data['choices'][0]['message']['content'].strip()
        else:
            print(f"Unexpected API response for messages: {messages}")
            return "Error extracting data"
    
    # Extract hobbies or experiences for analogies
    messages_experience = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": f"The person mentioned: '{transcript}'. Extract a hobby or personal experience they might have talked about and write one sentence of that so that we can use that for creating analogies in the future."}
    ]
    experience_summary = make_api_call(messages_experience)

    # Extract preferred explanation style
    messages_style = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": f"The person mentioned: '{transcript}'. Identify their preferred explanation style and return in one concise sentence."}
    ]
    style_summary = make_api_call(messages_style)

    return style_summary, experience_summary



def get_audio_file_info(audio_file_path):
    with wave.open(audio_file_path, 'rb') as wf:
        print(f"Channels: {wf.getnchannels()}")
        print(f"Sample width: {wf.getsampwidth()}")
        print(f"Frame rate: {wf.getframerate()}")
        print(f"Frame count: {wf.getnframes()}")

def convert_audio_to_required_format(audio_file_path, target_format='wav'):
    try:
        file_extension = os.path.splitext(audio_file_path)[1].lower()[1:]
        print(f"Original file extension: {file_extension}")
        if file_extension == target_format:
            return audio_file_path
        elif file_extension in ['webm', 'ogg']:
            audio = AudioSegment.from_file(audio_file_path, format=file_extension)
        else:
            audio = AudioSegment.from_wav(audio_file_path)

        audio = audio.set_frame_rate(16000)
        audio = audio.set_channels(1)
        temp_path = "temp_converted_audio.wav"
        audio.export(temp_path, format=target_format, codec='pcm_s16le')
        print(f"Audio exported to {temp_path}")
        return temp_path
    except Exception as e:
        print(f"Error converting audio: {e}")
        raise

def upload_to_assemblyai(filename):
    def read_file(filename, chunk_size=5242880):
        with open(filename, "rb") as _file:
            while True:
                data = _file.read(chunk_size)
                if not data:
                    break
                yield data

    api_token = '7f69bde78c5b48be96c4a49dc7b00ca9'
    headers = {"authorization": api_token}

    response = requests.post(
        "https://api.assemblyai.com/v2/upload",
        headers=headers,
        data=read_file(filename)
    )

    print(f"Upload response: {response.json()}")
    
    if response.status_code == 200:
        return response.json()["upload_url"]
    else:
        print(f"Failed to upload file, status code: {response.status_code}")
        return None
    
    
def speech_to_text(audio_file_path):
    try:
        api_token = '7f69bde78c5b48be96c4a49dc7b00ca9'
        headers = {
            'authorization': api_token,
            'content-type': 'application/json',
        }

        # Upload your local file to the AssemblyAI API
        with open(audio_file_path, "rb") as f:
            response = requests.post("https://api.assemblyai.com/v2/upload",
                                     headers=headers,
                                     data=f)

        upload_url = response.json()["upload_url"]

        return upload_url  # Return the upload_url instead of transcription_id

    except Exception as e:
        print(f"Error converting speech to text: {e}")
        return None


#for mathpix
def extract_image_content(image_path):
    """
    Extract content from an image using the Mathpix API.
    """
    r = requests.post("https://api.mathpix.com/v3/text",
        files={"file": open(image_path, "rb")},
        data={
            "options_json": json.dumps({
                "math_inline_delimiters": ["$", "$"],
                "rm_spaces": True
            })
        },
        headers={
            "app_id": APP_ID,
            "app_key": APP_KEY
        }
    )
    return json.dumps(r.json(), indent=4, sort_keys=True)


def get_gpt_response(user_query, image_content, user_style, user_hobby):
    ENDPOINT = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
    }
    
    
    messages = [
        {"role": "system", "content": 
            f"""You are a helpful and interesting personal tutor. 
            You can understand the the image content shown on the users screen. The content of the image might be returned to you (after some cv processing) as a text, latex, Smiles, or in some other form that you can understand. 
            Here is the image content: "{image_content}" .  
            Before preoceeding to answer the users question make sure you FULLY understand everything currently being shown on the screen. 
            You also know that they returned this as their preferred learning style: '{user_style}' 
            And they returned this as thier hobby:'{user_hobby}'. 
            Your task is to explain thier query in a way that answers them directly, but explains it in a way that is according to their learning style, and if seen to be necessary (be thoughtfully proactive), also uses very thoughful analogies that is relatable based on their hobby. 
            Be concise and succint as appropriate to fit a 1 minute voice explanation that is interesting and helpful to the user. (we are going to be returning your text in a voice form). 
          """},
        {"role": "user", "content": user_query}
    ]

    response = requests.post(ENDPOINT, headers=headers, json={"model": "gpt-4", "messages": messages})
    response_data = response.json()

    if 'choices' in response_data:
        return response_data['choices'][0]['message']['content'].strip()
    else:
        print(f"Unexpected API response for messages: {messages}")
        return "I'm sorry, I couldn't generate a response at the moment."

def text_to_voice(text):
    """
    Convert the given text to voice using Google's Text-to-Speech API.
    The function currently outputs an MP3 file.
    """
    
    client = texttospeech.TextToSpeechClient()
    input_text = texttospeech.SynthesisInput(text=text)
    
    voice = texttospeech.VoiceSelectionParams(language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

    response = client.synthesize_speech(input=input_text, voice=voice, audio_config=audio_config)

    output_audio_path = "output_voice_response.mp3"
    with open(output_audio_path, 'wb') as out:
        out.write(response.audio_content)

    return output_audio_path