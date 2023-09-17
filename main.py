from flask import Flask, request, jsonify
import config
from utils import identify_learning_style_and_hobby, speech_to_text, get_gpt_response, text_to_voice
import os

# Initialize Flask app and set Google credentials for cloud services
app = Flask(__name__)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.GOOGLE_CREDENTIALS_PATH

# A dictionary to store user information, e.g., learning style and hobby
USERS = {}

@app.route('/onboarding', methods=['POST'])
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


@app.route('/process-image', methods=['POST'])
def process_image():
    """
    Process an uploaded image and extract its content.
    Currently uses Mathpix for image content extraction.
    """

    # Retrieve the uploaded image from the request
    image_file = request.files.get('image_file')
    image_path = "curr.png"
    image_file.save(image_path)  # Save the uploaded image temporarily

    # Extract content from the image using Mathpix API
    image_content = extract_image_content(image_path)

    # Cleanup: remove the saved image after processing
    os.remove(image_path)

    # Return a success message and the extracted content
    return jsonify({"message": "Image processed successfully", "content": image_content}), 200

@app.route('/generate-response', methods=['POST'])
def generate_response():
    """
    Generate a response based on the uploaded image's content and user preferences.
    The function uses the content from the image and previously stored user data 
    (from the onboarding process) to generate a GPT response. The text response 
    is then converted to an audio format.
    """

    # Retrieve the uploaded image from the request
    image_file = request.files.get('image_file')
    image_path = "curr.png"
    image_file.save(image_path)  # Save the uploaded image temporarily

    # Extract content from the image using Mathpix API
    image_content = extract_image_content(image_path)

    # Get user data stored during the onboarding process
    user_data = USERS.get('default_user', {})
    user_style = user_data.get('style', '')
    user_hobby = user_data.get('hobby', '')

    # Generate a GPT-4 response based on the image content and user data
    gpt_response = get_gpt_response('', image_content, user_style, user_hobby)

    # Convert the text response to audio
    voice_response_path = text_to_voice(gpt_response)

    # Cleanup: remove the saved image after processing
    os.remove(image_path)

    # Return a success message and the path to the generated audio response
    return jsonify({"message": "Response generated successfully", "audio_path": voice_response_path}), 200

# Entry point for running the Flask app
if __name__ == '__main__':
    app.run(debug=True)
