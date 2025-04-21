import asyncio
# import os  # Removed os import
# from dotenv import load_dotenv # Removed dotenv import
# load_dotenv() # Removed dotenv call
import base64
import json
from uuid import uuid4
from datetime import datetime
from typing import Optional

import nltk
import redis
import websockets
import openai
import httpx
from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from nltk.tokenize import sent_tokenize
import uvicorn

# import config # Removed config import

# Initialize the FastAPI app
app = FastAPI()

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




# --- Hardcoded Configuration Variables ---
OPENAI_API_KEY = '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'
ELEVENLABS_API_KEY = 'fb1d27b5fb4d1ceb38083a558f24f1cd'
ASSEMBLYAI_TOKEN = "7f69bde78c5b48be96c4a49dc7b00ca9"
VOICE_ID = "CYw3kZ02Hs0563khs1Fj"
# --- End Hardcoded Variables ---


# Removed the check for OPENAI_API_KEY from environment

# OpenAI Configuration
# openai.api_key = OPENAI_API_KEY # This line is for older versions, not strictly needed
client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY) # Uses the hardcoded key

# Redis Configuration for Online Redis
REDIS_URI='redis://default:password@redis-14713.c258.us-east-1-4.ec2.redns.redis-cloud.com:14713'



# !!! --- START DEBUG PRINTS --- !!!
print("--- CONFIGURATION VALUES ---")
print(f"OPENAI_API_KEY used: '{OPENAI_API_KEY}'") # Print OpenAI key
print(f"ELEVENLABS_API_KEY used: '{ELEVENLABS_API_KEY}'")
print(f"ASSEMBLYAI_TOKEN used: '{ASSEMBLYAI_TOKEN}'")
print(f"VOICE_ID used: '{VOICE_ID}'")
print(f"REDIS_URI used: '{REDIS_URI}'") # Print Redis URI
print("--- END CONFIGURATION VALUES ---")
# !!! --- END DEBUG PRINTS --- !!!


# OpenAI Configuration
print("Initializing OpenAI client...") # <<< DEBUG PRINT
try:
    client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY) # Uses the hardcoded key
    print("OpenAI client initialized successfully.") # <<< DEBUG PRINT
except Exception as e:
    print(f"ERROR initializing OpenAI client: {e}") # <<< DEBUG PRINT
    raise # Re-raise the exception to stop the app if it fails


# Redis Configuration for Online Redis
print("Initializing Redis client...") # <<< DEBUG PRINT
try:
    redis_client = redis.from_url(REDIS_URI)
    # Test connection immediately
    print("Testing Redis connection...") # <<< DEBUG PRINT
    redis_client.ping() # <<< This will raise an error if connection/auth fails
    print("Redis connection successful (ping successful).") # <<< DEBUG PRINT
except redis.exceptions.AuthenticationError as auth_err:
    print(f"FATAL REDIS ERROR: Authentication failed. Check password in REDIS_URI. Error: {auth_err}") # <<< DEBUG PRINT
    raise # Stop the app
except redis.exceptions.ConnectionError as conn_err:
    print(f"FATAL REDIS ERROR: Connection failed. Check hostname, port, network access, or DNS. Error: {conn_err}") # <<< DEBUG PRINT
    raise # Stop the app
except Exception as e:
    print(f"FATAL REDIS ERROR: An unexpected error occurred during Redis initialization: {e}") # <<< DEBUG PRINT
    raise # Stop the app
















redis_client = redis.from_url(REDIS_URI)














# Global variables for storing the latest image path and transcript
latest_image_path = None
latest_transcript = ""
USERS = {}

# Pydantic model for transcript data
class Transcript(BaseModel):
    transcript: str

# Pydantic model for onboarding request data
class OnboardingRequest(BaseModel):
    text: Optional[str] = None

# Setup NLTK for sentence tokenization
def setup_nltk():
    nltk_data_path = 'nltk_data'
    # Check if the default path already exists or if NLTK can find 'punkt'
    try:
        sent_tokenize("Test sentence.")
    except LookupError:
        # If 'punkt' is not found, append the custom path and download if necessary
        nltk.data.path.append(nltk_data_path)
        if not os.path.exists(os.path.join(nltk_data_path, 'tokenizers', 'punkt')):
            if not os.path.exists(nltk_data_path):
                 os.makedirs(nltk_data_path) # Use makedirs to create parent dirs if needed
            print("NLTK 'punkt' not found. Downloading...")
            nltk.download('punkt', download_dir=nltk_data_path)
            print("Download complete.")

# Call the setup function at the start of the application
# Need to import os just for this NLTK setup part
import os
setup_nltk()

# Endpoint to clear image content
@app.post('/clear-image-content')
async def clear_image_content():
    global latest_image_path
    try:
        if latest_image_path and os.path.exists(latest_image_path):
            os.remove(latest_image_path)
            latest_image_path = None
            print("Previous image file deleted")

        redis_client.delete('latest_image_content')
        print("Cleared image content from Redis")

        return {"status": "cleared"}
    except Exception as e:
        print(f"Error in /clear-image-content: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint to get a token for AssemblyAI
@app.get("/token")
async def get_token():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'https://api.assemblyai.com/v2/realtime/token',
            json={'expires_in': 3600},
            headers={'authorization': ASSEMBLYAI_TOKEN} # Uses hardcoded token
        )
    return response.json()

# Endpoint to receive and store the final transcript
@app.post("/finalTranscript")
async def receive_final_transcript(transcript_data: Transcript):
    redis_client.set('latest_transcript', transcript_data.transcript)
    return {"status": "transcript_received"}

# WebSocket endpoint for handling real-time communication
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    latest_transcript = redis_client.get('latest_transcript')
    latest_transcript = latest_transcript.decode('utf-8') if latest_transcript else 'no query'
    await chat_completion(latest_transcript, websocket)

# Helper function to chunk text using NLTK
async def text_chunker(chunks):
    buffer = ""
    async for text in chunks:
        buffer += text
        # Use NLTK for sentence tokenization
        try:
            sentences = sent_tokenize(buffer)
            if len(sentences) > 1:
                yield " ".join(sentences[:-1]) + " "
                buffer = sentences[-1]
        except Exception as e:
            print(f"NLTK sentence tokenization error: {e}")
            # Fallback behavior: yield the buffer if it gets long or contains likely sentence enders
            if len(buffer) > 100 or any(p in buffer for p in ['.', '!', '?']):
                 yield buffer + " "
                 buffer = ""

    if buffer:
        yield buffer + " "


# Function to stream text-to-speech input
async def text_to_speech_input_streaming(voice_id, text_iterator, websocket):
    uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?model_id=eleven_monolingual_v1&output_format=pcm_24000"
    async with websockets.connect(uri) as elevenlabs_ws:
        await elevenlabs_ws.send(json.dumps({
            "text": " ",
            "voice_settings": {"stability": 0.5, "similarity_boost": True},
            "xi_api_key": ELEVENLABS_API_KEY, # Uses hardcoded key
        }))
        async def listen():
            while True:
                try:
                    message = await elevenlabs_ws.recv()
                    data = json.loads(message)
                    if data.get("audio"):
                        await websocket.send_json({"audio": data["audio"]})
                    elif data.get('isFinal'):
                        break
                except websockets.exceptions.ConnectionClosed:
                    print("Connection closed")
                    break
                except Exception as e:
                    print(f"An error occurred: {e}")
                    break
        listener_task = asyncio.ensure_future(listen())
        try:
            async for text in text_chunker(text_iterator):
                await elevenlabs_ws.send(json.dumps({"text": text, "try_trigger_generation": True}))
            await elevenlabs_ws.send(json.dumps({"text": ""}))
            await listener_task
        except Exception as e:
            print(f"An error occurred: {e}")
            listener_task.cancel()

# Endpoint for onboarding a new user
@app.post('/onboarding')
async def onboarding(request_data: OnboardingRequest):
    if request_data.text is None:
        raise HTTPException(status_code=400, detail="Text not provided")
    transcript = request_data.text
    style_summary, experience_summary = await identify_learning_style_and_hobby(transcript)
    USERS['default_user'] = {'style': style_summary, 'hobby': experience_summary}
    return {"message": "Onboarding successful", "style": style_summary, "experience": experience_summary}

# Function to identify learning style and hobby using OpenAI API
async def identify_learning_style_and_hobby(transcript):
    messages_experience = [
        {"role": "system", "content": "You are a helpful assistant that is concise."},
        {"role": "user", "content": f"This is the user's response: '{transcript}'. Identify any mentioned hobbies or professional experience."}
    ]
    messages_style = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": f"This is the user's response: '{transcript}'. Identify the individual's preferred learning style."}
    ]
    # Uses the globally initialized 'client' which has the hardcoded key
    experience_response = await client.chat.completions.create(
        model="gpt-4",
        messages=messages_experience
    )
    style_response = await client.chat.completions.create(
        model="gpt-4",
        messages=messages_style
    )
    experience_summary = experience_response.choices[0].message.content.strip()
    style_summary = style_response.choices[0].message.content.strip()
    return style_summary, experience_summary

# Function to handle chat completion using OpenAI API
async def chat_completion(query: str, websocket: WebSocket):
    image_content = redis_client.get('latest_image_content').decode('utf-8') if redis_client.get('latest_image_content') else None
    user_data = USERS.get('default_user', {})
    user_style = user_data.get('style', 'default style if not found')
    user_hobby = user_data.get('hobby', 'default hobby if not found')
    print(f"This was the users query: {query}")
    print(f"This was the user submitted hobby: {user_hobby}")
    print(f"This was the user submitted learning style: {user_style}")
    messages = [
        {
            "role": "system",
            "content":
            f"""You are a helpful personal conversational tutor. Your name is Vortex. You are a personal tutor that makes learning intuitive.
                The users query is being converted from their speech to text so just know that the query might be a bit different to what they said and you can thoughtfully infer the right thing. You don't have to tell the users this just say you are a conversational ai tutor that can both hear what they say, see whats on their screen and know how to be their best personal tutor.
                You can understand the the image content shown on the users screen. You using the image vision processing to do this.

                Before proceeding to answer the users question make sure you FULLY understand everything currently being shown on the screen. (On the case that they upload an image)
                You also know that they returned this as their preferred learning style: ('{user_style}')

                So your task is to explain their query in a way that answers them directly in relation to helping them understand whats on the screen according to their learning style.

                Additionally You also know that they returned this as their hobby: ('{user_hobby}'). So you can use analogies related to their hobby to help them understand better using associative chaining.

                Do not go further to use analogies if the users query doesn't warrant this. Please be thoughtful and you don't need to always use analogies for a simple direct question that warrants a direct useful response.

                IF and only IF requested by the user, you can explain it in a way that uses a thoughtful analogy that is relatable based on ONE of their hobbies.

                But remember your goal is to respond to the users query directly. These are just additional contexts you can use as per the users query."

                VERY IMPORTANT:  Make sure that the text you return is in a way that can be read out loud as words. We are using a text to speech to return your response to the user as sound. Especially for mathematical stuffs make sure not to output your respoonse in a way that can not be read by the text to speech easily as a word!
            """
        },
        {"role": "user", "content": query}
    ]
    if image_content:
        # Construct the image message correctly for GPT-4 Vision
        vision_message_content = [{"type": "text", "text": query}]
        try:
            # Ensure image_content is valid base64 before appending
            base64.b64decode(image_content) # Test decoding
            vision_message_content.append(
                 {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_content}"}}
            )
            # Replace the last simple text message with the combined text+image message
            messages[-1] = {
                 "role": "user",
                 "content": vision_message_content
            }
        except Exception as img_err:
            print(f"Error processing image content for OpenAI: {img_err}. Sending text only.")
            # Keep the original simple text message if image processing fails


    # Uses the globally initialized 'client' which has the hardcoded key
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=1000,
        stream=True,
        temperature=0.5
    )
    async def text_iterator(response):
        async for part in response:
            # Check if delta exists and has content
            delta = getattr(part.choices[0], 'delta', None)
            content = getattr(delta, 'content', None) if delta else None

            if content:
                #print(content, end='', flush=True) # Debug print stream
                yield content

            # Check finish reason using getattr for safety
            finish_reason = getattr(part.choices[0], 'finish_reason', None)
            if finish_reason == 'stop':
                 #print("\nStream finished.") # Debug print stream end
                 return # Exit the generator

    await text_to_speech_input_streaming(VOICE_ID, text_iterator(response), websocket)


# Helper function to encode an image in base64
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Endpoint to upload an image
@app.post('/upload-image')
async def upload_image(file: UploadFile = File(...)):
    global latest_image_path
    # Need os module for path manipulation here
    import os
    try:
        # Clear previous image if exists
        if latest_image_path and os.path.exists(latest_image_path):
             try:
                 os.remove(latest_image_path)
                 latest_image_path = None
                 print("Previous temporary image file deleted.")
             except OSError as e:
                 print(f"Error deleting previous image {latest_image_path}: {e}")

        # Create a unique temporary file name
        image_key = str(uuid4())
        temp_dir = "./temp_images" # Store images in a sub-directory
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        temp_file_path = os.path.join(temp_dir, f"temp_image_{image_key}.png")

        # Save uploaded file temporarily
        with open(temp_file_path, "wb") as buffer:
            content = await file.read() # Read async
            buffer.write(content)

        # Encode and store in Redis
        base64_image = base64.b64encode(content).decode('utf-8') # Encode content directly
        redis_client.set('latest_image_content', base64_image)

        # Update the global path
        latest_image_path = temp_file_path
        print(f"Image saved to {latest_image_path}")

        return JSONResponse(content={"message": "Image uploaded successfully"}, status_code=200)
    except Exception as e:
        print(f"Error during image upload: {e}")
        # Clean up temp file if it exists and error occurred
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
             try:
                 os.remove(temp_file_path)
             except OSError as cleanup_e:
                 print(f"Error cleaning up temp file {temp_file_path}: {cleanup_e}")
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint to get the processed image
@app.get('/get-processed-image')
async def get_processed_image():
    global latest_image_path
    import os # Need os for path check
    try:
        if latest_image_path and os.path.exists(latest_image_path):
            return FileResponse(latest_image_path, media_type='image/png')
        # Attempt to retrieve from Redis if path missing but content exists? (Optional)
        elif latest_image_path:
            print(f"File not found at path: {latest_image_path}")
            raise HTTPException(status_code=404, detail="Image file not found on server.")
        else:
            print("No latest image path set")
            raise HTTPException(status_code=404, detail="No image has been uploaded recently.")
    except Exception as e:
        print(f"Error in get_processed_image: {e}")
        print(f"Exception details: {type(e).__name__}, Args: {e.args}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Use port 5001 as decided earlier
    uvicorn.run(app, host="0.0.0.0", port=5001)