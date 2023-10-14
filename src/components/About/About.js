import React, { useEffect, useCallback, useReducer } from "react";
import ReactLoading from "react-loading";
import DragDropFiles from "./DragDropFiles"; 
import "./About.css"; 
import axios from "axios";
import ReactAudioPlayer from "react-audio-player";
import Recorder from 'recorder-js';

const initialState = {
    record: false,
    audioURL: '',
    audio: null,
    isPredict: false,
    currFiles: null,
    processing: false,
    received: false,
    isLLMLoading: false,
    loadChat: false,
    talking: false,
    transcriptionId: null,
    responseReceived: false,
    timeoutId: null,
    processedTranscriptionIds: [],
    pollingAttempts: 0,
    MAX_POLLING_ATTEMPTS: 5,
    pollingInProgress: false,
    requestCompleted: false
};

function reducer(state, action) {
    if(!action.type) {
        console.error('Action type is undefined:', action);
        return state;
    }

    switch (action.type) {
        case 'SET_STATE':
            return { ...state, ...action.payload };
        default:
            console.error('Unexpected action:', action);
            return state;
    }
}

function About() {
    const [state, dispatch] = useReducer(reducer, initialState);
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();

    const checkResponseReady = useCallback(async () => {
      if (state.responseReceived || state.requestCompleted || state.processedTranscriptionIds.includes(state.transcriptionId)) {
          return;
      }
  
      clearTimeout(state.timeoutId);
  
      if (state.pollingAttempts >= state.MAX_POLLING_ATTEMPTS) {
          dispatch({ type: 'SET_STATE', payload: { processing: false, pollingInProgress: false, pollingAttempts: 0 } });
          return;
      }
  
      try {
          const response = await axios.get(`http://127.0.0.1:5000/get-response/${state.transcriptionId}`);
          if (response.status === 200) {
              if (state.timeoutId) {
                  clearTimeout(state.timeoutId);
                  dispatch({ type: 'SET_STATE', payload: { timeoutId: null } });
              }
              dispatch({
                  type: 'SET_STATE',
                  payload: {
                      audio: response.data.audio,
                      processing: false,
                      talking: true,
                      responseReceived: true,
                      pollingAttempts: 0,
                      pollingInProgress: false,
                      requestCompleted: true,
                      processedTranscriptionIds: [...state.processedTranscriptionIds, state.transcriptionId]
                  }
              });
          } else if (response.status === 202) {
              dispatch({
                  type: 'SET_STATE',
                  payload: {
                      timeoutId: setTimeout(checkResponseReady, 1000),
                      pollingAttempts: state.pollingAttempts + 1
                  }
              });
          }
      } catch (error) {
          dispatch({ type: 'SET_STATE', payload: { processing: false } });
      }
  }, [state.transcriptionId, state.timeoutId, state.pollingAttempts, state.MAX_POLLING_ATTEMPTS, state.responseReceived, state.requestCompleted, state.processedTranscriptionIds]);
  
  useEffect(() => {
      if (state.transcriptionId && !state.pollingInProgress && !state.responseReceived && !state.requestCompleted && !state.processedTranscriptionIds.includes(state.transcriptionId)) {
          dispatch({ type: 'SET_STATE', payload: { pollingInProgress: true } });
          checkResponseReady();
      } else if (state.responseReceived || state.requestCompleted) {
          dispatch({
              type: 'SET_STATE',
              payload: {
                  pollingInProgress: false,
                  responseReceived: false,
                  requestCompleted: false,
                  pollingAttempts: 0
              }
          });
      }
  
      return () => {
          if (state.timeoutId) {
              clearTimeout(state.timeoutId);
          }
      };
  }, [state.transcriptionId, state.pollingInProgress, state.responseReceived, state.requestCompleted, state.processedTranscriptionIds, checkResponseReady]);
  
    useEffect(() => {
        if (!state.talking && !state.isLLMLoading) {
            dispatch({ 
                type: 'SET_STATE', 
                payload: { 
                    audioURL: '', 
                    audio: null, 
                    received: false, 
                    isPredict: false, 
                    transcriptionId: null, 
                    responseReceived: false, 
                    requestCompleted: false, 
                    pollingInProgress: false 
                } 
            });
        }
    }, [state.talking, state.isLLMLoading]);

    const obtainLLMResponse = async () => {
        if (!state.audioURL || !state.currFiles) {
            return;
        }

        const audioBlob = await fetch(state.audioURL).then(response => response.blob());
        const formData = new FormData();
        formData.append('audio_query', audioBlob, 'audio.wav');
        formData.append("file", state.currFiles[0]);

        dispatch({ type: 'SET_STATE', payload: { processing: true, loadChat: true } });

        try {
            const response = await axios.post("http://127.0.0.1:5000/generate-response", formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });

            dispatch({ type: 'SET_STATE', payload: { transcriptionId: response.data.transcription_id, loadChat: false, responseReceived: false } });
        } catch (error) {
            dispatch({ type: 'SET_STATE', payload: { processing: false, loadChat: false } });
        }
    };

    const startRecording = () => {
        dispatch({ type: 'SET_STATE', payload: { audioURL: '', audio: null } });
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then((stream) => {
                const rec = new Recorder(audioContext);
                rec.init(stream).then(() => {
                    rec.start();
                    dispatch({ type: 'SET_STATE', payload: { recorder: rec, record: true } });
                });
            });
    };

    const stopRecording = () => {
        if (state.recorder) {
            state.recorder.stop()
                .then(({ blob }) => {
                    const audioURL = URL.createObjectURL(blob);
                    dispatch({ type: 'SET_STATE', payload: { audioURL: audioURL, record: false, isPredict: true } });
                });
        }
    };

    const handleFile = (files, uploaded) => {
        dispatch({ type: 'SET_STATE', payload: { currFiles: files, isPredict: state.audioURL && files !== null } });
        if (uploaded) {
            dispatch({ type: 'SET_STATE', payload: { received: true } });
        }
    };

    return (
      <div className="about-container">
          <div className="dropzone-container">
              <DragDropFiles handleFile={handleFile} />
              <h1 className="record-title">Ask any question about your image!</h1>
              {state.record ? (
                  <button className="recording-button" onClick={stopRecording}>Stop Speaking</button>
              ) : (
                  <>
                      <button className="recording-button" onClick={startRecording}>Start Speaking</button>
                      {state.audioURL && <button className="predict-button" disabled={!state.isPredict} onClick={obtainLLMResponse}>Get Answer</button>}
                  </>
              )}
              <div className="audio-recorder-container">
                  {state.audioURL && <ReactAudioPlayer src={state.audioURL} controls />}
                  {state.record && <ReactLoading className="test-loader" type="bars" color="#a317a3" />}
              </div>
              {state.processing && <ReactLoading type="bars" color="#a317a3" className="loader" />}
          </div>
          <div className="chat-container">
              <h1 style={{ color: "white", fontWeight: "lighter" }}>InsightAI personal assistant</h1>
              <div className="chat-box">
                  <div className={"audio-wrapper"}>
                      <img className="avatar" src={require("./avatar.png")} alt="Avatar" /> 
                      {state.loadChat && <ReactLoading type="bubbles" color="#17a34a" className="loader" />}
                      {state.audio && (
                          <ReactAudioPlayer
                              src={`data:audio/wav;base64,${state.audio}`}
                              controls={true}
                              autoPlay={true}
                              onPlay={() => dispatch({ type: 'SET_STATE', payload: { isLLMLoading: true } })}
                              onEnded={() => dispatch({ type: 'SET_STATE', payload: { isLLMLoading: false } })}
                              onPause={() => dispatch({ type: 'SET_STATE', payload: { isLLMLoading: false } })}
                          />
                      )}
                      {state.talking && state.isLLMLoading && <ReactLoading type="bars" color="#17a34a" className="loader" />}
                      {!state.talking && state.received && (
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
                  {!state.received && <h1 className="filler">Upload an image and question</h1>}
              </div>
          </div>
      </div>
    );
}

export default About;
