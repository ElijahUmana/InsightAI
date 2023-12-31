import asyncio
import nltk
import websockets
import json
import openai
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import httpx
from pydantic import BaseModel
import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
import json
import requests
from typing import Optional
import config
from datetime import datetime
import os
from uuid import uuid4
import redis
from openai import AsyncOpenAI
import base64
from nltk.tokenize import sent_tokenize

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Configuration
OPENAI_API_KEY = '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'
ELEVENLABS_API_KEY = 'fb1d27b5fb4d1ceb38083a558f24f1cd'
ASSEMBLYAI_TOKEN = "7f69bde78c5b48be96c4a49dc7b00ca9"
VOICE_ID = "CYw3kZ02Hs0563khs1Fj"
ELEVENLABS_API_KEY = 'fb1d27b5fb4d1ceb38083a558f24f1cd'




# OpenAI Configuration
openai.api_key = OPENAI_API_KEY

client = AsyncOpenAI(api_key=OPENAI_API_KEY)


def setup_nltk():
    nltk_data_path = 'nltk_data'
    nltk.data.path.append(nltk_data_path)

    if not os.path.exists(nltk_data_path):
        os.mkdir(nltk_data_path)
        nltk.download('punkt', download_dir=nltk_data_path)

# Call the setup function at the start of your application
setup_nltk()

latest_image_path = None 

@app.post('/clear-image-content')
async def clear_image_content():
    global latest_image_path
    try:
        # Delete the previous image file if it exists
        if latest_image_path and os.path.exists(latest_image_path):
            os.remove(latest_image_path)
            latest_image_path = None
            print("Previous image file deleted")

        # Clear the image content from Redis
        redis_client.delete('latest_image_content')
        print("Cleared image content from Redis")

        return {"status": "cleared"}
    except Exception as e:
        print(f"Error in /clear-image-content: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Redis Configuration for Online Redis
REDIS_URI = 'redis://default:1qD008ljjrwxgto4d0wndxxPsVwcrhd6@redis-17813.c245.us-east-1-3.ec2.cloud.redislabs.com:17813'
redis_client = redis.from_url(REDIS_URI)


class Transcript(BaseModel):
    transcript: str
# Temporary storage for transcript (not ideal for production)
latest_transcript = ""


@app.get("/token")
async def get_token():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'https://api.assemblyai.com/v2/realtime/token',
            json={'expires_in': 3600},
            headers={'authorization': ASSEMBLYAI_TOKEN}
        )
    return response.json()

@app.post("/finalTranscript")
async def receive_final_transcript(transcript_data: Transcript):
    redis_client.set('latest_transcript', transcript_data.transcript)
    return {"status": "transcript_received"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    latest_transcript = redis_client.get('latest_transcript')
    latest_transcript = latest_transcript.decode('utf-8') if latest_transcript else 'no query'
    await chat_completion(latest_transcript, websocket)

async def text_chunker(chunks):
    """Improved split text into chunks using NLTK for natural sentence boundaries."""
    buffer = ""

    async for text in chunks:
        buffer += text
        sentences = sent_tokenize(buffer)

        # If more than one sentence is identified, yield all but the last one
        if len(sentences) > 1:
            yield " ".join(sentences[:-1]) + " "
            buffer = sentences[-1]

    # Yield any remaining text in the buffer
    if buffer:
        yield buffer + " "

async def text_to_speech_input_streaming(voice_id, text_iterator, websocket):
    uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?model_id=eleven_monolingual_v1&output_format=pcm_24000"

    async with websockets.connect(uri) as elevenlabs_ws:
        await elevenlabs_ws.send(json.dumps({
            "text": " ",
            "voice_settings": {"stability": 0.5, "similarity_boost": True},
            "xi_api_key": ELEVENLABS_API_KEY,
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

            # Wait until all audio data is received before closing the connection
            await listener_task
        except Exception as e:
            print(f"An error occurred: {e}")
            listener_task.cancel()
 
 


USERS = {}


class OnboardingRequest(BaseModel):
    text: Optional[str] = None

@app.post('/onboarding')
async def onboarding(request_data: OnboardingRequest):
    """
    This route handles the onboarding process for a user.
    It now expects a JSON payload with the user's text input.
    """

    # Validate and extract data from request
    if request_data.text is None:
        raise HTTPException(status_code=400, detail="Text not provided")

    transcript = request_data.text

    # Await the result of identify_learning_style_and_hobby function
    style_summary, experience_summary = await identify_learning_style_and_hobby(transcript)

    # Store the extracted data for the user
    USERS['default_user'] = {'style': style_summary, 'hobby': experience_summary}

    # Return a success message along with the extracted data
    return {"message": "Onboarding successful", "style": style_summary, "experience": experience_summary}


async def identify_learning_style_and_hobby(transcript):
    """
    Identify the learning style and hobby from the given transcript using OpenAI API.
    """
    messages_experience = [
        {"role": "system", "content": "You are a helpful assistant that is concise."},
        {"role": "user", "content": f"This is the user's response: '{transcript}'. Identify any mentioned hobbies or professional experience."}
    ]

    messages_style = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": f"This is the user's response: '{transcript}'. Identify the individual's preferred learning style."}
    ]

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
    

async def chat_completion(query: str, websocket: WebSocket):
    image_content = redis_client.get('latest_image_content').decode('utf-8') if redis_client.get('latest_image_content') else None
    
    user_data = USERS.get('default_user', {})
    user_style = user_data.get('style', 'default style if not found')
    user_hobby = user_data.get('hobby', 'default hobby if not found')
    print(f"This was the users query: {query}")
    print(f"this was the user submitted hobby: {user_hobby}")
    print(f"this was the user submitted learning style: {user_style}")

    # Prepare message payload for OpenAI API including the image
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
        image_message = {
            "role": "user",
            "content": [
                {"type": "text", "text": query},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_content}"}}
            ]
        }
        messages.append(image_message)

    response = await client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=messages,
        max_tokens=1000, 
        stream=True,
        temperature=0.5
    )
    
    async def text_iterator(response):
        async for part in response:
            for choice in part.choices:
                content = choice.delta.content
                if content:
                    yield content
                if content is None and choice.finish_reason == 'stop':
                    return

    await text_to_speech_input_streaming(VOICE_ID, text_iterator(response), websocket)



    


latest_image_content = None  # Variable to hold the latest image content


latest_image_key = None
processed_images = {}

    
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

@app.post('/upload-image')
async def upload_image(file: UploadFile = File(...)):
    global latest_image_path
    try:
        # Clear previous image and its content
        await clear_image_content()

        image_key = str(uuid4())
        temp_file_name = f"./temp_image_{image_key}.png"
        with open(temp_file_name, "wb") as buffer:
            buffer.write(file.file.read())

        # Convert the image to base64 and store in Redis
        base64_image = encode_image(temp_file_name)
        redis_client.set('latest_image_content', base64_image)

        latest_image_path = temp_file_name
        return JSONResponse(content={"message": "Image uploaded successfully"}, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    
@app.get('/get-processed-image')
async def get_processed_image():
    global latest_image_path
    try:
        # Check if the latest image path is set and the file exists
        if latest_image_path and os.path.exists(latest_image_path):
            return FileResponse(latest_image_path, media_type='image/png')
        elif latest_image_path:
            print(f"File not found at path: {latest_image_path}")
            raise HTTPException(status_code=404, detail="File not found")
        else:
            print("No latest image path set")
            raise HTTPException(status_code=404, detail="No image content available")
    except Exception as e:
        print(f"Error in get_processed_image: {e}")
        # Additional logging for debugging
        print(f"Exception details: {type(e).__name__}, Args: {e.args}")
        raise HTTPException(status_code=500, detail=str(e))


    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)    