
import requests
import json
from utils import speech_to_text, convert_audio_to_required_format, get_audio_file_info
from flask import Flask, request, send_file, jsonify, Response
from utils import speech_to_text, convert_audio_to_required_format, get_audio_file_info
from utils import identify_learning_style_and_hobby, speech_to_text, get_gpt_response, text_to_voice, extract_image_content
from flask_cors import CORS
import os
import base64
import config
import time
import mimetypes
import pydub
from flask import send_from_directory
from os import path


APP_KEY = "3c9a7ad798ebeb8d5c6b74d30b902c38aa1c56cd1cc4d78f10cdc4ae4bbd88aa"
APP_ID = "insightai_c0fe0f_bf33f1"


api = Flask(__name__)
CORS(api)



os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.GOOGLE_CREDENTIALS_PATH

# A dictionary to store user information, e.g., learning style and hobby
USERS = {}


@api.route('/onboarding', methods=['POST'])
def onboarding():
    """
    This route handles the onboarding process for a user. 
    It expects an audio file where the user talks about their preferences.
    The function saves the audio file, converts it to text, and then extracts 
    the learning style and any hobby or personal experience mentioned by the user.
    The results are stored in a USERS dictionary for future use.
    After processing, all temporary files are deleted.
    """

    audio_file = request.files.get('audio_file')
    audio_file.save("audio.wav")  # Save the audio file temporarily

    # Convert the audio file to text
    transcript = speech_to_text("audio.wav")

    # Extract the user's learning style and any mentioned hobby/experience
    style_summary, experience_summary = identify_learning_style_and_hobby(transcript)

    # Store the extracted data for the user
    USERS['default_user'] = {'style': style_summary, 'hobby': experience_summary}

    # Cleanup: remove temporary files
    os.remove("audio.wav")

    # Check if the converted audio file exists before removing it
    if os.path.exists("temp_converted_audio.wav"):
        os.remove("temp_converted_audio.wav")

    # Return a success message along with the extracted data
    return jsonify({"message": "Onboarding successful", 
                    "style": style_summary, 
                    "experience": experience_summary}), 200
    
    
USER_STYLE = "receive detailed step by step explanations, understanding intuition behind concepts is essential."
USER_HOBBY = "Listening to music and basketball"


PROCESSED_IMAGES = {}

@api.route('/upload-image', methods=["POST"])
def upload_image():
    print("Received image at this endpoint")
    try:
        image_file = request.files["file"]
        if image_file:
            filepath = "./curr.png"
            image_file.save(filepath)
            print(f"Image saved to {filepath}")

            # Process the image content using the Mathpix API
            image_content = extract_image_content("./curr.png")
            
            # Save the processed content in the PROCESSED_IMAGES dictionary
            PROCESSED_IMAGES['default_image'] = image_content
            return jsonify({"message": "Image uploaded and processed successfully"}), 200
        else:
            return jsonify({"error": "No image file provided"}), 400
    except Exception as e:
        print(f"Error uploading and processing image: {e}")
        return jsonify({"error": "Server error during image upload and processing"}), 500


@api.route('/get-processed-image', methods=["GET"])
def get_processed_image():
    try:
        image_url = "http://127.0.0.1:5000/curr.png"
        print(f"Trying to retrieve image from {image_url}")
        
        # Return the URL of the processed image
        return jsonify({"imageUrl": image_url}), 200
    except Exception as e:
        print(f"Error retrieving processed image: {e}")
        return jsonify({"error": "Could not retrieve processed image"}), 500


from flask import send_file

@api.route('/curr.png', methods=["GET"])
def serve_image():
    try:
        # Provide the path to the image
        image_path = "./curr.png"
        return send_file(image_path, mimetype='image/png')

    except Exception as e:
        print(f"Error serving image: {e}")
        return jsonify({"error": "Could not serve the image"}), 500


RESPONSES = {}  # Dictionary to store audio responses keyed by transcription_id

def convert_mp3_to_wav(mp3_path):
    audio = pydub.AudioSegment.from_mp3(mp3_path)
    wav_path = mp3_path.replace('.mp3', '.wav')
    audio.export(wav_path, format="wav")
    return wav_path

@api.route('/generate-response', methods=['POST'])
def generate_response():
    print("Received request at /generate-response.")
    audio_query_path = None
    try:
        audio_query_file = request.files.get('audio_query')
        if audio_query_file is None:
            return jsonify({"error": "Missing audio_query file"}), 400

        audio_query_path = "audio_query.wav"
        audio_query_file.save(audio_query_path)

        get_audio_file_info(audio_query_path)  # assuming this function is necessary for your use case

        # Convert the audio to the required format before uploading
        converted_audio_path = convert_audio_to_required_format(audio_query_path)

        api_token = '7f69bde78c5b48be96c4a49dc7b00ca9'
        headers = {
            'authorization': api_token,
            'content-type': 'application/json',
        }

        # Upload your local file to the AssemblyAI API
        with open(converted_audio_path, "rb") as f:
            response = requests.post("https://api.assemblyai.com/v2/upload",
                                     headers=headers,
                                     data=f)

        upload_url = response.json()["upload_url"]

        # The webhook URL where AssemblyAI will send the transcription result
        webhook_url = "https://adf7-98-15-195-180.ngrok-free.app/assemblyai-webhook"

        # Create a JSON payload containing the audio_url parameter and the webhook_url parameter
        data = {
            "audio_url": upload_url,
            "webhook_url": webhook_url
        }

        # Make a POST request to the AssemblyAI API endpoint with the payload and headers
        response = requests.post('https://api.assemblyai.com/v2/transcript', json=data, headers=headers)
        transcription_id = response.json()['id']

        return jsonify({
            "message": "Transcription process started successfully",
            "transcription_id": transcription_id,
            "upload_url": upload_url  # Including the upload_url for your reference
        }), 200

    except Exception as e:
        print(f"Error generating response: {e}")
        return jsonify({"error": "Server error"}), 500
    finally:
        if audio_query_path and os.path.exists(audio_query_path):
            os.remove(audio_query_path)


def fetch_transcription_text(transcription_id):
    headers = {
        "authorization": "7f69bde78c5b48be96c4a49dc7b00ca9"
    }
    try:
        transcription_result_response = requests.get(
            f"https://api.assemblyai.com/v2/transcript/{transcription_id}",
            headers=headers
        )
        transcription_result_response.raise_for_status()  # Check for HTTP errors
        transcription_result = transcription_result_response.json()
        return transcription_result.get('text')
    except requests.exceptions.HTTPError as err:
        print(f"HTTP error occurred: {err}")
    except Exception as err:
        print(f"An error occurred: {err}")

    return None


PROCESSED_TRANSCRIPTION_IDS = set()


@api.route('/assemblyai-webhook', methods=['POST'])
def assemblyai_webhook():
    print("Received webhook from AssemblyAI.")
    try:
        request_data = request.get_json()
        if 'transcript_id' not in request_data or 'status' not in request_data:
            print("Invalid webhook data:", request_data)
            return jsonify({"error": "Invalid webhook data"}), 400

        transcription_id = request_data['transcript_id']
        status = request_data['status']
        print(f"Transcription status for {transcription_id}: {status}")


        if transcription_id in PROCESSED_TRANSCRIPTION_IDS:
            print(f"Already processed transcription ID {transcription_id}")
            return jsonify({"message": "Already processed"}), 200

        if status == 'completed':
            # Fetch the transcription text from AssemblyAI
            PROCESSED_TRANSCRIPTION_IDS.add(transcription_id)
            
            transcript_result = fetch_transcription_text(transcription_id)
            if transcript_result is None:
                print(f"Error fetching transcription text for {transcription_id}")
                return jsonify({"error": "Error fetching transcription text"}), 500

            print(f"Transcription result for {transcription_id}: {transcript_result}")

            # Assuming 'default_image' and 'default_user' are placeholders for actual data
            image_content = PROCESSED_IMAGES.get('default_image', '')
            user_data = USERS.get('default_user', {})

            gpt_response = get_gpt_response(
                transcript_result, image_content,
                USER_STYLE, USER_HOBBY
            )

            print(f"GPT-3 response for {transcription_id}: {gpt_response}")

            voice_response_path_mp3 = text_to_voice(gpt_response)
            print(f"MP3 response path: {voice_response_path_mp3}")  # Added logging

            voice_response_path_wav = convert_mp3_to_wav(voice_response_path_mp3)
            print(f"WAV response path: {voice_response_path_wav}")  # Added logging

            if not os.path.exists(voice_response_path_wav):
                print(f"Error: WAV file not found at {voice_response_path_wav}")
                return jsonify({"error": "Server error"}), 500

            # Store the response using transcription_id as the key
            RESPONSES[transcription_id] = {"audio_path": voice_response_path_wav}

            print(f"Updated RESPONSES dictionary: {RESPONSES}")

            return jsonify({"message": "Response generated and saved successfully"}), 200
        else:
            print(f"Transcription not completed for {transcription_id}: {status}")
            return jsonify({"message": "Transcription not completed"}), 202

    except Exception as e:
        print(f"Error processing webhook: {e}")
        return jsonify({"error": "Server error"}), 500




@api.route('/get-response/<string:transcription_id>', methods=['GET'])
def get_response(transcription_id):
    print(f"Received request at /get-response for transcription_id: {transcription_id}")
    print(f"Current state of RESPONSES dictionary: {RESPONSES}")
    response_data = RESPONSES.get(transcription_id)
    
    if response_data is None or response_data['audio_path'] is None:
        return jsonify({"status": "not_ready"}), 202

    audio_path = response_data['audio_path']
    try:
        with open(audio_path, 'rb') as file:
            audio_data = file.read()

        audio_base64 = base64.b64encode(audio_data).decode('utf-8')  # Encoding audio data to base64
        return jsonify({"status": "ready", "audio": audio_base64}), 200  # Returning JSON with status and base64 audio data

    except Exception as e:
        print(f"Error reading audio data: {e}")
        return jsonify({"error": "Server error"}), 500


if __name__ == '__main__':
    api.run(debug=True)

