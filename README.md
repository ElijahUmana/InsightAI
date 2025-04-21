# InsightAI: A Personalized AI Learning Companion

## Overview

InsightAI is an integrated learning environment that allows users to pursue their curiosity with unparalleled depth and precision. This innovative app blends advanced image recognition and state-of-the-art language models to provide context-rich, voice-over explanations. Tailored to individual learning styles, InsightAI offers a seamless, interactive, and enriching learning environment.

*Tutor Interaction in InsightAI*
<img width="1688" alt="Screenshot 2023-11-30 at 1 01 46 PM" src="https://github.com/ElijahUmana/InsightAI/assets/121345656/7d1440a0-ea24-43b4-94e2-96d50dab1e52">


## Features
- **Fine-Tuned Image Recognition**: Utilizes the OpenAI CLIP model to interpret a wide range of on-screen content, from complex mathematical equations to intricate chemical diagrams.
- **Voice-Over Explanations**: Integrates users' voice queries with visual understanding, providing real-time, context-rich explanations through advanced Large Language Models (LLMs).
- **Personalized Learning**: Adapts to individual learning styles by incorporating user-provided information about hobbies, experiences, and preferred learning methods.
- **Real-Time Conversational AI Tutor**: Offers feedback and assistance using personalized analogies and associative chainings, enhancing the learning experience.
- **Screen Understanding**: Analyzes on-screen content in real-time to provide contextual feedback.
- **Chrome Extension**: Enables easy capture and upload of educational content from any screen to InsightAI, streamlining the learning process.

## How It Works
1. **Onboarding**: Users complete a form detailing their hobbies, experiences, and learning preferences.
2. **Conversational AI Tutor**: Engage with a real-time tutor that provides tailored feedback and assistance.
3. **Screen Interaction**: Users can upload or display images for the tutor to analyze and respond to voice queries with accurate, real-time explanations.
4. **Chrome Extension**: Capture and upload screen content to InsightAI for seamless learning across different platforms.

## Technical Architecture
- **Backend**: Built with FastAPI and asynchronous functions for efficient backend performance.
- **Image Recognition**: Employs OpenAI CLIP for screen content understanding.
- **AI Language Model**: Uses GPT-4 with advanced prompt engineering for personalized user interaction.
- **Text-to-Speech**: Integrates with Eleven Labs' text-to-speech, delivering responses with minimal latency via WebSocket.
- **Database**: Utilizes Redis for temporary data storage and MongoDB for persistent user data.
- **Frontend**: Developed using React and Node.js, optimized for asynchronous functions and WebSocket to enhance application responsiveness.
- **Chrome Extension**: Created with JavaScript, HTML, CSS, and manifest.json for a smooth user experience.
- **Deployment**: Containerized with Docker and deployed on Heroku for both frontend and backend services.
