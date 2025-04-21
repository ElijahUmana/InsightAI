import React, { useEffect, useState, useCallback, useReducer, useRef } from "react";
import ReactLoading from "react-loading";
import DragDropFiles from "./DragDropFiles";
import "./About.css";
import axios from "axios";
import ReactAudioPlayer from "react-audio-player";
import Recorder from 'recorder-js';
import { useLocation } from 'react-router-dom';
import { useNavigate } from 'react-router-dom';
import RecordRTC, { StereoAudioRecorder } from 'recordrtc';




const initialState = {
    currFiles: null,
    processing: false,
    received: false,
    isLLMLoading: false,
    loadChat: false,
    transcriptionId: null,
    responseReceived: false,
    timeoutId: null,
    processedTranscriptionIds: [],
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

function dataURLToBlob(dataurl) {
    var arr = dataurl.split(','), mime = arr[0].match(/:(.*?);/)[1],
        bstr = atob(arr[1]), n = bstr.length, u8arr = new Uint8Array(n);
    while(n--){
        u8arr[n] = bstr.charCodeAt(n);
    }
    return new Blob([u8arr], {type:mime});
}



function About() {
    const [isUploaded, setIsUploaded] = useState(false);
    const [state, dispatch] = useReducer(reducer, initialState);
    const [processedImage, setProcessedImage] = useState('');
    const [isRedirected, setIsRedirected] = useState(false);
    const navigate = useNavigate();
    const [files, setFiles] = useState(null);
    const [isRecording, setIsRecording] = useState(false);
    const [isStopping, setIsStopping] = useState(false);
    const [isPlaying, setIsPlaying] = useState(false);
    const transcriptsRef = useRef(''); 
    const recorderRef = useRef(null);
    const assemblySocketRef = useRef(null);
    let audioContext;
    let audioBufferQueue = [];
    let lastBufferEndTime = 0;
    let adaptiveBufferSize = 1;
    const [transcript, setTranscript] = useState(''); // New state for the real-time transcript
    const [displayRecordingStatus, setDisplayRecordingStatus] = useState(false); // New state
    

    const [showVideo, setShowVideo] = useState(false);
    const [audioChunkCounter, setAudioChunkCounter] = useState(0);
    const endAudioTimeoutRef = useRef();

    const [displayVideo, setDisplayVideo] = useState(false);
    
    const [displayText, setDisplayText] = useState(false);
    const [countdown, setCountdown] = useState(null);
    const [currentCount, setCurrentCount] = useState(null);
    const backendUrl = 'http://localhost:5001';

    


    
    useEffect(() => {
        let timeout;
        if (!showVideo) {
            timeout = setTimeout(() => {
                setDisplayText(true);
            }, 1000); // same duration as the fade-out animation
        } else {
            setDisplayText(false);
        }
        return () => clearTimeout(timeout);
    }, [showVideo]);


    useEffect(() => {
        if (audioChunkCounter > 0) {
            setShowVideo(true);
            setDisplayRecordingStatus(false); // Start the video when there's an audio chunk to play
        }
    
        return () => {
            if (endAudioTimeoutRef.current) {
                clearTimeout(endAudioTimeoutRef.current);
            }
        };
    }, [audioChunkCounter]);

    useEffect(() => {
        if (showVideo) {
            setDisplayVideo(true);
        } else {
            setTimeout(() => {
                setDisplayVideo(false);
            }, 1000); // 1s delay which is the duration of the fade-out animation
        }
    }, [showVideo]);
    
    




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
                const response = await axios.get('https://http://localhost:5001/get-processed-image', { responseType: 'blob' });
                if (response.status === 200) {
                    const blobUrl = URL.createObjectURL(response.data);
                    setProcessedImage(blobUrl);
                    setFiles([new File([response.data], 'redirected-image.png', { type: 'image/png' })]);
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

    
    useEffect(() => {
        if (isRedirected) {
            getImageFromUrlParam();
        }
    }, [isRedirected]);

    const handleFile = (files, uploaded) => {
        dispatch({ type: 'SET_STATE', payload: { currFiles: files, isPredict: state.audioURL && files !== null } });
        if (uploaded) {
            dispatch({ type: 'SET_STATE', payload: { received: true } });
        }
    };

    



    useEffect(() => {
        return () => {
            if (audioContext) {
                audioContext.close();
            }
        };
    }, [audioContext]);


    
    

    const playAudioData = async (audioData) => {
        if (!audioContext) {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            audioContext = new AudioContext({ sampleRate: 24000 });
        }
        if (audioContext.state === "suspended") {
            await audioContext.resume();
        }
        const arrayBuffer = Uint8Array.from(atob(audioData), c => c.charCodeAt(0)).buffer;
        const numberOfChannels = 1;
        const length = arrayBuffer.byteLength / 2;
        const sampleRate = 24000;
    
        const audioBuffer = audioContext.createBuffer(numberOfChannels, length, sampleRate);
        const channelData = audioBuffer.getChannelData(0);
    
        const dataView = new DataView(arrayBuffer);
        for (let i = 0; i < length; i++) {
            channelData[i] = dataView.getInt16(i * 2, true) / 32768.0;
        }
        audioBufferQueue.push(audioBuffer);
    
        setAudioChunkCounter(prev => prev + 1);  // Increase the audio chunk counter for each received chunk
    
        if (!isPlaying && audioBufferQueue.length >= adaptiveBufferSize) {
            playBufferedAudio();
        }
    };

    const playBufferedAudio = () => {
        if (audioBufferQueue.length === 0) {
            // Since the queue is empty, delay the check for one second
            setTimeout(() => {
                // Check if the audio context has finished playing
                if (audioContext.currentTime >= lastBufferEndTime) {
                    setIsPlaying(false);
                    setShowVideo(false); // Stop the video only if all audio has been played
                } else {
                    // If there's still audio left to play, set a timeout to check again later
                    setTimeout(playBufferedAudio, (lastBufferEndTime - audioContext.currentTime) * 4000);
                }
            }, 2000);  // 1000 milliseconds delay
            return;
        }
    
        setIsPlaying(true);
        adaptiveBufferSize = Math.max(2, adaptiveBufferSize - 1);
        const buffer = audioBufferQueue.shift();
        const source = audioContext.createBufferSource();
        source.buffer = buffer;
        source.connect(audioContext.destination);
    
        if (lastBufferEndTime < audioContext.currentTime) {
            lastBufferEndTime = audioContext.currentTime;
        }
        source.start(lastBufferEndTime);
        lastBufferEndTime += buffer.duration;
        source.onended = playBufferedAudio;
    };
    

    const startResponseSocket = () => {
        const responseSocket = new WebSocket('ws://localhost:5001/ws');
        responseSocket.onmessage = (message) => {
            const res = JSON.parse(message.data);
            if (res.audio) {
                if (isPlaying) {
                    adaptiveBufferSize = Math.min(5, adaptiveBufferSize + 1);
                }
                playAudioData(res.audio);
            }
        };
        responseSocket.onerror = (event) => {
            console.error(event);
            if (responseSocket) responseSocket.close();
        };
        responseSocket.onclose = () => {
            console.log('Response socket closed');
        };
    };

    const finalizeTranscription = async () => {
        console.log("Transcript to be sent to backend:", transcriptsRef.current);
        await fetch('http://localhost:5001/finalTranscript', {
            method: 'POST',
            body: JSON.stringify({ transcript: transcriptsRef.current }),
            headers: { 'Content-Type': 'application/json' }
        });

        startResponseSocket();
        setIsRecording(false);

        if (assemblySocketRef.current) {
            assemblySocketRef.current.onmessage = null;
            assemblySocketRef.current.onerror = null;
            assemblySocketRef.current.onclose = null;
            assemblySocketRef.current.close();
            assemblySocketRef.current = null;
        }
    };

    const stopRecording = async () => {
        if (isRecording && !isStopping) {  // Check if it is recording and not already in the process of stopping
            setIsStopping(true);
            setTimeout(async () => {
                setIsStopping(false);
                audioBufferQueue = [];
                lastBufferEndTime = 0;
    
                if (audioContext && audioContext.state !== 'closed') {
                    audioContext.close().then(() => {
                        audioContext = null;
                    });
                }
    
                if (recorderRef.current) {
                    recorderRef.current.stopRecording(() => {
                        if (assemblySocketRef.current && assemblySocketRef.current.readyState === WebSocket.OPEN) {
                            assemblySocketRef.current.send(JSON.stringify({ 'end_session': true }));
                        }
                    });
                    recorderRef.current = null;
                }
    
                finalizeTranscription();
            }, 3000);
        }
    };
    
    const run = async () => {
        if (!isRecording && !isStopping) {  
            setIsRecording(true);
            transcriptsRef.current = '';  
    
            const response = await fetch('http://localhost:5001/token');
            const data = await response.json();
            const { token } = data;
    
            assemblySocketRef.current = new WebSocket(`wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000&token=${token}`);
            
    
            assemblySocketRef.current.onmessage = (message) => {
                const res = JSON.parse(message.data);
                if (res.message_type === "FinalTranscript") {
                    console.log("Received transcription:", res.text);
                    transcriptsRef.current += (transcriptsRef.current ? ' ' : '') + res.text;
                    setTranscript(transcriptsRef.current);
                }
            };
    
            assemblySocketRef.current.onopen = () => {
                navigator.mediaDevices.getUserMedia({ audio: true })
                    .then((stream) => {
                        
                        const AudioContext = window.AudioContext || window.webkitAudioContext;
                        const audioContext = new AudioContext();
    
                        // Create an audio source from the stream
                        const source = audioContext.createMediaStreamSource(stream);
    
                        // Create a gain node
                        const gainNode = audioContext.createGain();
    
                        // Connect source to gain
                        source.connect(gainNode);
    
                        // Adjust the gain value
                        gainNode.gain.value = 1.2;  // Increase volume
    
                        // Create a destination for the audio
                        const dest = audioContext.createMediaStreamDestination();
    
                        // Connect gain to destination
                        gainNode.connect(dest);
    
                        recorderRef.current = new RecordRTC(dest.stream, {
                            type: 'audio',
                            mimeType: 'audio/webm;codecs=pcm',
                            recorderType: StereoAudioRecorder,
                            timeSlice: 250,
                            desiredSampRate: 16000,
                            numberOfAudioChannels: 1,
                            bufferSize: 4096,
                            audioBitsPerSecond: 128000,
                            ondataavailable: (blob) => {
                                const reader = new FileReader();
                                reader.onload = () => {
                                    const base64data = reader.result;
                                    if (assemblySocketRef.current && assemblySocketRef.current.readyState === WebSocket.OPEN) {
                                        assemblySocketRef.current.send(JSON.stringify({ audio_data: base64data.split('base64,')[1] }));
                                    }
                                };
                                reader.readAsDataURL(blob);
                            },
                        });
    
                        recorderRef.current.startRecording();
                    })
                    .catch((err) => console.error(err));
            };
    
            assemblySocketRef.current.onerror = (event) => {
                console.error(event);
                if (assemblySocketRef.current) assemblySocketRef.current.close();
            };
    
            assemblySocketRef.current.onclose = () => {
                assemblySocketRef.current = null;
            };
        } else if (isRecording && !isStopping) {  
            stopRecording();
        }
    };

    const stopWithoutFinalizing = () => {
        if (recorderRef.current) {
            recorderRef.current.stopRecording();
            recorderRef.current = null;
        }
        if (audioContext && audioContext.state !== 'closed') {
            audioContext.close().then(() => {
                audioContext = null;
            });
        }
        setIsRecording(false);
        setCurrentCount(null);
        setDisplayRecordingStatus(false);
    };
    

    const initialDelayTimer = useRef(null);
    const countdownTimer = useRef(null);
    const releasedDuringCountdown = useRef(false); // Use useRef for this flag
    
    useEffect(() => {
        let countdownInterval;
    
        const handleKeyDown = async (e) => {
            if (e.code === 'Space' && !isRecording && !isStopping) {
                setCurrentCount(3);
                releasedDuringCountdown.current = false; // Reset the flag on a new space press
    
                initialDelayTimer.current = setTimeout(async () => {
                    await run();
    
                    countdownInterval = setInterval(() => {
                        setCurrentCount((prevCount) => {
                            if (prevCount > 1) {
                                return prevCount - 1;
                            } else {
                                clearInterval(countdownInterval);
                                if (!releasedDuringCountdown.current) {
                                    // Only start listening if spacebar wasn't released during countdown
                                    setDisplayRecordingStatus(true);
                                }
                                return null;
                            }
                        });
                    }, 300);
                }, 20);
            }
        };
    
        const handleKeyUp = (e) => {
            if (e.code === 'Space' && !isStopping) {
                if (currentCount && currentCount > 0) {
                    clearTimeout(initialDelayTimer.current);
                    clearInterval(countdownInterval); // Clear the correct interval
                    releasedDuringCountdown.current = true;
                    setDisplayRecordingStatus(false);
                    stopWithoutFinalizing();
                    setCurrentCount(null);
                } else {
                    stopRecording();
                    setCurrentCount(null);
                    setDisplayRecordingStatus(false);
                }
            }
        };
    
        if (!isPlaying) {
            document.addEventListener('keydown', handleKeyDown);
            document.addEventListener('keyup', handleKeyUp);
        }
    
        return () => {
            document.removeEventListener('keydown', handleKeyDown);
            document.removeEventListener('keyup', handleKeyUp);
        };
    }, [isRecording, isStopping, currentCount, run, stopWithoutFinalizing, stopRecording, isPlaying]);
    
     


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



                {/* make the space bar thing the same height as the recording button css hieght  */}
                

                <div className="record-title">
                    <h4>
                        <p>
                            {isStopping 
                                ? 'Stopping...' 
                                : (currentCount 
                                    ? <>Start talking in... <strong>{currentCount}</strong></> 
                                    : (displayRecordingStatus 
                                        ? 'Listening...' 
                                        : 'Press and hold the space bar to start talking. Release to stop.')
                                    )
                                
                            }
                        </p>
                    </h4>

                    <div className="transcripts">
                        <div className="transcript-bar">
                            <p>{transcript ? `Your voice transcripts: "${transcript}"` : 'Your transcripts will show here'}</p>
                        </div>
                    </div>
                </div>








                <div className="audio-recorder-container">
                    {state.audioURL && <ReactAudioPlayer src={state.audioURL} controls />}
                    {state.record && <ReactLoading className="test-loader" type="bars" color="#a317a3" />}
                </div>
            </div>
            <div className="chat-container">
                <div className="chat-box">
                    <div className="flex-container">
                        <div className={"audio-wrapper"}>
                            <img className="avatar" src={require("./avatar.png")} alt="Avatar" />
                        </div>
                        <div className="media-container">
                            {displayText && <h9 className="chat-text" style={{ color: "white", fontWeight: "lighter" }}>Hi there! Ask me whatever questions you may have  :)</h9>}
                            {displayVideo && (
                            <div key="videoKey" className={showVideo ? "video-cropper video-fade-in" : "video-cropper video-fade-out"}>
                                <video 
                                    className="video-to-crop"
                                    width="320" 
                                    height="240" 
                                    loop 
                                    autoPlay
                                >
                                    <source src={`${process.env.PUBLIC_URL}/wave.mov`} type="video/mp4" />
                                    Your browser does not support the video tag.
                                </video>
                            </div>
                        )}

                        </div>
                    </div>
                </div>
            </div>




        </div>
    );
}

export default About;
