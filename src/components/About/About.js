import React, { useState, useEffect, useCallback, useRef } from "react";
import ReactLoading from "react-loading";
import DragDropFiles from "./DragDropFiles";
import "./About.css";
import axios from "axios";
import ReactAudioPlayer from "react-audio-player";
import Recorder from 'recorder-js';

function About() {
  const [record, setRecord] = useState(false);
  const [audioURL, setAudioURL] = useState('');
  const [audio, setAudio] = useState(null);
  const [isPredict, setIsPredict] = useState(false);
  const [currFiles, setCurrFiles] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [received, setReceived] = useState(false);
  const [isLLMLoading, setIsLLMLoading] = useState(false);
  const [loadChat, setLoadChat] = useState(false);
  const [talking, setTalking] = useState(false);
  const [transcriptionId, setTranscriptionId] = useState(null);
  const audioContext = new (window.AudioContext || window.webkitAudioContext)();
  const [recorder, setRecorder] = useState(null);
  const [responseReceived, setResponseReceived] = useState(false);
  const [timeoutId, setTimeoutId] = useState(null);
  const [pollingAttempts, setPollingAttempts] = useState(0);
  const MAX_POLLING_ATTEMPTS = 6; // Adjust this based on your requirements
  const [pollingInProgress, setPollingInProgress] = useState(false);

function base64ToBlob(base64, mimeType='') {
  const byteCharacters = atob(base64);
  const byteNumbers = new Array(byteCharacters.length);

  for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
  }

  const byteArray = new Uint8Array(byteNumbers);
  return new Blob([byteArray], {type: mimeType});
}


const checkResponseReady = useCallback(async () => {
  clearTimeout(timeoutId);  // Clear the timeout to prevent overlapping
  console.log('Polling attempt:', pollingAttempts + 1);

  if (responseReceived || pollingAttempts >= MAX_POLLING_ATTEMPTS) {
      console.error(pollingAttempts >= MAX_POLLING_ATTEMPTS ? "Max polling attempts reached" : "Response received");
      setProcessing(false);
      setPollingInProgress(false); // Ensure polling doesn't proceed
      setPollingAttempts(0); // Reset the attempts
      return;
  }

  try {
      const response = await axios.get(`http://127.0.0.1:5000/get-response/${transcriptionId}`);
      
      if (response.status === 200) {
          const responseData = response.data;
          if(responseData.status === 'ready') {
              console.log('Audio response received.');
              const audioBlob = base64ToBlob(responseData.audio, 'audio/wav');  // Convert base64 to blob
              const audioURL = URL.createObjectURL(audioBlob);
              setAudio(audioURL); 
              setProcessing(false);
              setTalking(true);
              setResponseReceived(true);
              setPollingAttempts(0); 
              clearTimeout(timeoutId);
              setPollingInProgress(false);  
          } else {
              console.error('Response received but not ready.');
              setProcessing(false);
          }
      } else if (response.status === 202) { 
          console.log('Response not ready, scheduling another poll.');
          const id = setTimeout(checkResponseReady, 10000); 
          setTimeoutId(id);
          setPollingAttempts(prev => prev + 1);
      } else {
          console.error('Unexpected response status:', response.status); 
          setProcessing(false);
      }
  } catch (error) {
      console.error("Error checking response readiness:", error);
      setProcessing(false);
      clearTimeout(timeoutId);
  }
}, [transcriptionId, responseReceived, timeoutId, pollingAttempts, pollingInProgress]);


// This useEffect sets up polling when transcriptionId changes
useEffect(() => {
  if (transcriptionId && !pollingInProgress && !responseReceived) {
      console.log('Transcription ID received, starting to poll for response.');
      setPollingInProgress(true); 
      checkResponseReady();
  }

  return () => {
      if (timeoutId) clearTimeout(timeoutId);
  };
}, [transcriptionId, pollingInProgress, responseReceived]);


// This useEffect listens for the responseReceived state and cleans up
useEffect(() => {
  if (responseReceived) {
    clearTimeout(timeoutId);
    setPollingInProgress(false);
  }

  return () => {
    setResponseReceived(false);  // Reset the state after the response is received
    setTranscriptionId(null);    // Reset the transcription ID as well
  };
}, [responseReceived]);

const obtainLLMResponse = async () => {
    if (!audioURL || !currFiles) {
        console.error("No audioURL or image set. Please ensure you've recorded audio and uploaded an image.");
        return;
    }

    const audioBlob = await fetch(audioURL).then(response => response.blob());
    const formData = new FormData();
    formData.append('audio_query', audioBlob, 'audio.wav');
    formData.append("file", currFiles[0]);

    setProcessing(true);
    setLoadChat(true);

    try {
        const response = await axios.post("http://127.0.0.1:5000/generate-response", formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });

        console.log('Response from /generate-response received.');
        setTranscriptionId(response.data.transcription_id);
        setLoadChat(false);
        // setPollingInProgress(false); // Reset polling in progress flag after obtaining response
    } catch (error) {
        console.error("Error in obtainLLMResponse:", error.response ? error.response.data : error.message);
        setProcessing(false);
        setLoadChat(false);
    }


    setResponseReceived(false);  
};



  const startRecording = () => {
    setAudioURL('');
    setAudio(null);
    navigator.mediaDevices.getUserMedia({ audio: true })
      .then((stream) => {
        const rec = new Recorder(audioContext);
        rec.init(stream).then(() => {
          rec.start();
          setRecorder(rec);
          setRecord(true);
        });
      });
  };

  const stopRecording = () => {
    if (recorder) {
      recorder.stop()
        .then(({ blob }) => {
          const audioURL = URL.createObjectURL(blob);
          setAudioURL(audioURL);
          setRecord(false);
          setIsPredict(true);
        });
    }
  };

  const handleFile = (files, uploaded) => {
    setCurrFiles(files);
    let pred = audioURL && files !== null ? true : false;
    setIsPredict(pred);
    if (uploaded) {
      console.log("Image uploaded and processed.");
      setReceived(true);  
    }
  };

  return (
    <div className="about-container">
      <div className="dropzone-container">
        <DragDropFiles handleFile={handleFile} />
        <h1 className="record-title">Ask any question about your image!</h1>
        {record ? (
          <button className="recording-button" onClick={stopRecording}>Stop Speaking</button>
        ) : (
          <>
            <button className="recording-button" onClick={startRecording}>Start Speaking</button>
            {audioURL && <button className="predict-button" disabled={!isPredict} onClick={obtainLLMResponse}>Get Answer</button>}
          </>
        )}
        <div className="audio-recorder-container">
          {audioURL && <ReactAudioPlayer src={audioURL} controls />}
          {record && <ReactLoading className="test-loader" type="bars" color="#a317a3" />}
        </div>
        {processing && <ReactLoading type="bars" color="#a317a3" className="loader" />}
      </div>
      <div className="chat-container">
        <h1 style={{ color: "white", fontWeight: "lighter" }}>InsightAI personal assistant</h1>
        <div className="chat-box">
          <div className={"audio-wrapper"}>
            <img className="avatar" src={require("./avatar.png")} alt="Avatar" />
            {loadChat && <ReactLoading type="bubbles" color="#17a34a" className="loader" />}
            {audio && (
              <ReactAudioPlayer
                src={audio}
                controls={true}
                autoPlay={true}
                onPlay={() => setIsLLMLoading(true)}
                onEnded={() => setIsLLMLoading(false)}
                onPause={() => setIsLLMLoading(false)}
              />
            )}
            {talking && isLLMLoading && <ReactLoading type="bars" color="#17a34a" className="loader" />}
            {!talking && received && (
              <div style={{
                  minHeight: "30px",
                  color: "white",
                  fontSize: "20px",
                  marginTop: "10px",
                  fontWeight: "20px",
                }}>
                <text>Great question, give me a minute to think this through!</text>
              </div>
            )}
          </div>
          {!received && <h1 className="filler">Upload an image and question</h1>}
        </div>
      </div>
    </div>
  );
}

export default About;
