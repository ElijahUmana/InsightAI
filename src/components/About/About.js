import React, { useEffect, useState, useCallback, useReducer, useRef } from "react";
import ReactLoading from "react-loading";
import DragDropFiles from "./DragDropFiles";
import "./About.css";
import axios from "axios";
import ReactAudioPlayer from "react-audio-player";
import Recorder from 'recorder-js';
import { useLocation } from 'react-router-dom';
import { useNavigate } from 'react-router-dom';




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
    if (!action.type) {
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

const clickedStyle = {
    backgroundColor: '#1e7e34',  // Darker green when clicked
};

const defaultStyle = {
    backgroundColor: '#28a745',  // Original green color
};

function About() {
    const [isUploaded, setIsUploaded] = useState(false);
    const [state, dispatch] = useReducer(reducer, initialState);
    const [processedImage, setProcessedImage] = useState('');
    const [isRedirected, setIsRedirected] = useState(false);
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const navigate = useNavigate();
    const [files, setFiles] = useState(null);
    const [buttonStyle, setButtonStyle] = useState(defaultStyle);



    const recordingRef = useRef(false);

    const handleKeyDown = useCallback((event) => {
        if (event.code === 'Space' && !recordingRef.current) {
            event.preventDefault();  // Prevent any default behavior
            console.log('Space bar pressed down, starting recording'); 
            startRecording();
        }
    }, []);  // Empty dependency array
    
    const handleKeyUp = useCallback((event) => {
        if (event.code === 'Space' && recordingRef.current) {
            event.preventDefault();  // Prevent any default behavior
            console.log('Space bar released, stopping recording');  // Add this line
            stopRecording();
        }
    }, []);  // Empty dependency array
    
    
    useEffect(() => {
        // Add global event listeners
        window.addEventListener('keydown', handleKeyDown);
        window.addEventListener('keyup', handleKeyUp);
    
        // Clean up event listeners on component unmount
        return () => {
            window.removeEventListener('keydown', handleKeyDown);
            window.removeEventListener('keyup', handleKeyUp);
        };
    }, [handleKeyDown, handleKeyUp]);  // Dependency array with handleKeyDown and handleKeyUp


    const checkRedirected = () => {
        const params = new URLSearchParams(location.search);
        return params.has('redirected');  // Check for 'redirected' URL parameter
    };

    useEffect(() => {
        setIsRedirected(checkRedirected());
    }, []);



    useEffect(() => {
        const fetchProcessedImage = async () => {
            try {
                const response = await axios.get('http://127.0.0.1:5000/get-processed-image');
                if (response.status === 200) {
                    const imageUrl = response.data.imageUrl;
                    setProcessedImage(imageUrl);
                    fetch(imageUrl)
                        .then(response => response.blob())  // Convert the response to a blob
                        .then(blob => {
                            const file = new File([blob], 'redirected-image.png', { type: 'image/png' });
                            setFiles([file]);  // Update the files state with the obtained file
                            setIsUploaded(true);  // Set isUploaded to true here
                        })
                        .catch(error => console.error('Failed to fetch image file:', error));
                } else {
                    console.error('Failed to fetch the processed image:', response.statusText);
                }
            } catch (error) {
                console.error('Error fetching the processed image:', error);
            }
        };
    
        
        if (isRedirected) {
            fetchProcessedImage();
        }
    }, [isRedirected, setFiles]);
    
    
        useEffect(() => {
        if (isRedirected) {
            setIsUploaded(true);
        }
    }, [isRedirected]);


    useEffect(() => {
        dispatch({ type: 'SET_STATE', payload: { currFiles: files } });
    }, [files]);
    
    
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
                        timeoutId: setTimeout(checkResponseReady, 500),
                        pollingAttempts: state.pollingAttempts + 1
                    }
                });
            }
        } catch (error) {
            dispatch({ type: 'SET_STATE', payload: { processing: false } });
        }
    }, [state.transcriptionId, state.timeoutId, state.pollingAttempts, state.MAX_POLLING_ATTEMPTS, state.responseReceived, state.requestCompleted, state.processedTranscriptionIds]);

    const location = useLocation();

    const getImageFromUrlParam = () => {
        const params = new URLSearchParams(location.search);
        const imageDataUrl = params.get('image');
        if (imageDataUrl) {
            const imageBlob = dataURLToBlob(imageDataUrl);
            const file = new File([imageBlob], 'screenshot.png', { type: 'image/png' });
            handleFile([file], true);
            // Remove the image parameter from the URL
            params.delete('image');
            navigate('?' + params.toString(), { replace: true });
        }
    };
    

    const clearProcessedImage = () => {
        setProcessedImage(null);
    };

    const dataURLToBlob = (dataURL) => {
        const binary = atob(dataURL.split(',')[1]);
        const array = [];
        for (let i = 0; i < binary.length; i++) {
            array.push(binary.charCodeAt(i));
        }
        return new Blob([new Uint8Array(array)], { type: 'image/png' });
    };
    
    useEffect(() => {
        if (isRedirected) {
            getImageFromUrlParam();
        }
    }, [isRedirected]);

    

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
        console.log('startRecording called');
        dispatch({ type: 'SET_STATE', payload: { audioURL: '', audio: null } });
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then((stream) => {
                const rec = new Recorder(audioContext);
                rec.init(stream).then(() => {
                    rec.start();
                    recordingRef.current = rec;
                    dispatch({ type: 'SET_STATE', payload: { recorder: rec, record: true } });
                    console.log('Recording started');
                });
            })
            .catch(error => console.error('Error starting recording:', error));
    };
    
    const stopRecording = () => {
        console.log('stopRecording called');
        if (recordingRef.current) {
            // Delay stopping the recording by 500 milliseconds
            setTimeout(() => {
                recordingRef.current.stop()
                    .then(({ blob }) => {
                        const audioURL = URL.createObjectURL(blob);
                        dispatch({ type: 'SET_STATE', payload: { audioURL: audioURL, record: false, isPredict: true } });
                        console.log('Recording stopped, audioURL:', audioURL);
                    })
                    .catch(error => console.error('Error stopping recording:', error));
                recordingRef.current = null;
            }, 500);
        } else {
            console.error('No recorder instance found');
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
            <DragDropFiles
                    handleFile={handleFile}
                    processedImage={processedImage}
                    clearProcessedImage={clearProcessedImage}
                    isUploaded={isUploaded}
                    setIsUploaded={setIsUploaded}
                    files={files}  // Pass files as prop
                    setFiles={setFiles}  // Pass setFiles as prop
                />


                <h1 className="record-title">Ask any question about your image!</h1>
                {state.record ? (
                    <button className="recording-button" onClick={stopRecording}>Stop Speaking</button>
                ) : (
                    <>
                        <button className="recording-button" onClick={startRecording}>Start Speaking</button>
                        {state.audioURL && (processedImage || isUploaded) && (
            <button 
                className="btn btn-success predict-button"
                style={buttonStyle}
                onMouseDown={() => setButtonStyle(clickedStyle)}
                onMouseUp={() => setButtonStyle(defaultStyle)}
                onMouseLeave={() => setButtonStyle(defaultStyle)}
                onClick={obtainLLMResponse}
            >
                Get Answer
            </button>
        )}

                    </>
                )}

                <div className="audio-recorder-container">
                    {state.audioURL && <ReactAudioPlayer src={state.audioURL} controls />}
                    {state.record && <ReactLoading className="test-loader" type="bars" color="#a317a3" />}
                </div>
            </div>
            <div className="chat-container">
                <h1 style={{ color: "white", fontWeight: "lighter" }}>InsightAI Assistant</h1>
                <div className="chat-box">
                    <div className={"audio-wrapper"}>
                        <img className="avatar" src={require("./avatar.png")} alt="Avatar" />
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
                    </div>
                </div>
            </div>
        </div>
    );
}

export default About;
