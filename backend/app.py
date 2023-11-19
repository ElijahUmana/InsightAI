import asyncio
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
ELEVENLABS_API_KEY = '589fdbe084808d33dd3edf3bcd4f230c'
ASSEMBLYAI_TOKEN = "7f69bde78c5b48be96c4a49dc7b00ca9"
VOICE_ID = "CYw3kZ02Hs0563khs1Fj"



# OpenAI Configuration
openai.api_key = OPENAI_API_KEY

class Transcript(BaseModel):
    transcript: str
# Temporary storage for transc ript (not ideal for production)
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
    global latest_transcript
    latest_transcript = transcript_data.transcript
    return {"status": "transcript_received"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await chat_completion(latest_transcript, websocket)

async def text_chunker(chunks):
    """Split text into chunks, ensuring to not break sentences."""
    splitters = (".", ",", "?", "!", ";", ":", "—", "-", "(", ")", "[", "]", "}", " ")
    buffer = ""
    async for text in chunks:
        if buffer.endswith(splitters):
            yield buffer + " "
            buffer = text
        elif text.startswith(splitters):
            yield buffer + text[0] + " "
            buffer = text[1:]
        else:
            buffer += text

    if buffer:
        yield buffer + " "

async def text_to_speech_input_streaming(voice_id, text_iterator, websocket):
    uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?model_id=eleven_monolingual_v1&output_format=pcm_24000"

    async with websockets.connect(uri) as elevenlabs_ws:
        await elevenlabs_ws.send(json.dumps({
            "text": " ",
            "voice_settings": {"stability": 0.2, "similarity_boost": True},
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

async def chat_completion(query: str, websocket: WebSocket):
    
        # Assuming 'default_image' and 'default_user' are placeholders for actual data
    image_content = PROCESSED_IMAGES.get('default_image', '')
    
    user_data = USERS.get('default_user', {})
    user_style = user_data.get('style', 'default style if not found')
    user_hobby = user_data.get('hobby', 'default hobby if not found')

    response = await openai.ChatCompletion.acreate(
        model='gpt-4', 
            messages=[
        {"role": "system", "content": 
            f"""You are a helpful personal conversational tutor. Your name is Vortex. You are a personal tutor that makes learning intuitive.
            The users query is being converted from their speech to text so just know that the query might be a bit different to what they said and you can thoughtfully infer the right thing. You don't have to tell the users this just say you are a conversational ai tutor that can both hear what they say, see whats on their screen and know how to be their best personal tutor. 
            
            You can understand the the image content shown on the users screen. The content of the image might be returned to you (after some cv processing) as a text, or latex. 
            
            Here is the image content: ( "{image_content}" .)  Make sure to only pay attention to the useful part of the image content. The cv processing might provide extraneous informarion about the image. 
            
            Before proceeding to answer the users question make sure you FULLY understand everything currently being shown on the screen.
            
            If its in latex form make sure you covert it internally so something generally readable. You shouldn't be responding to the user in latex format but in the normal languages the teacher would use like "raised to the power of" for ^ or stuffs like that. 
            
            You also know that they returned this as their preferred learning style: ('{user_style}') 
            
            So your task is to explain thier query in a way that answers them directly in relation to helping them understand whats on the screen according to their learning style.
            
            Additionally You also know that they returned this as thier hobby: ( '{user_hobby}'. )
            
            Do not go further to use analogies if the users query doesn't warrant this. Please be thoughtful and you don't need to always use analogies for a simple direct question that warrants a direct useful response. 
            
            IF and only IF requested by the user, you can explain it in a way that uses a thoughful analogy that is relatable based on ONE of their hobbies. 
            
            But remember your goal is to respond to the users query directly. These are just additional contexts you can use as per the users query. 
            
            Return a concise and succint as appropriate response to fit a 1 minute voice over. Remeber to make sure your transcript reads symbols in the normal way the student will understand. We will be directly converting your text to speech using google text to speech and play it to the user. 
        
          """},
        {"role": "user", "content": query}
    ],
        temperature=0.4, 
        stream=True
    )

    async def text_iterator():
        async for chunk in response:
            delta = chunk['choices'][0]["delta"]
            if 'content' in delta:
                yield delta["content"]
            else:
                break

    await text_to_speech_input_streaming(VOICE_ID, text_iterator(), websocket)
    



#FLASK UTILS

APP_KEY = "3c9a7ad798ebeb8d5c6b74d30b902c38aa1c56cd1cc4d78f10cdc4ae4bbd88aa"
APP_ID = "insightai_c0fe0f_bf33f1"

def identify_learning_style_and_hobby(transcript):
    """
    Identify the learning style and hobby from the given transcript.
    Uses OpenAI API to analyze the transcript content.
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
    
    # Extract hobbies or experiences
    messages_experience = [
        {"role": "system", "content": "You are a helpful assistant that is concise."},
        {"role": "user", "content": f"This is the users response: '{transcript}'. From that identify any mentioned hobbies OR professional experience. Respond ONLY in one sentence the identified hobby/professional experience."}
    ]
    experience_summary = make_api_call(messages_experience)

    # Extract preferred explanation style
    messages_style = [
        {"role": "system", "content": "You are a helpful assistant that is concise. "},
        {"role": "user", "content": f"This is the users response: '{transcript}'. From that identify the individual's preferred learning style that was said. Respond ONLY in one sentence the identified said preferred learning style or any style that was said"}
    ]
    style_summary = make_api_call(messages_style)

    return style_summary, experience_summary



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


##FLASK ROUTES
# A dictionary to store user information, e.g., learning style and hobby
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

    # Extract the user's learning style and any mentioned hobby/experience
    style_summary, experience_summary = identify_learning_style_and_hobby(transcript)

    # Store the extracted data for the user
    USERS['default_user'] = {'style': style_summary, 'hobby': experience_summary}

    # Cleanup: remove temporary files (if any)

    # Return a success message along with the extracted data
    return {"message": "Onboarding successful", "style": style_summary, "experience": experience_summary}

    

PROCESSED_IMAGES = {}

@app.post('/upload-image')
async def upload_image(file: UploadFile = File(...)):  # FastAPI way to handle file uploads
    try:
        filepath = "./curr.png"
        with open(filepath, "wb") as buffer:
            buffer.write(file.file.read())
        print(f"Image saved to {filepath}")

        image_content = extract_image_content(filepath)
        PROCESSED_IMAGES['default_image'] = image_content
        return JSONResponse(content={"message": "Image uploaded and processed successfully"}, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/get-processed-image')
async def get_processed_image():
    try:
        image_url = "http://127.0.0.1:8000/curr.png"
        return JSONResponse(content={"imageUrl": image_url}, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/curr.png')
async def serve_image():
    try:
        return FileResponse('./curr.png', media_type='image/png')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)    