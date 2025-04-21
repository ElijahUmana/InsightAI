import { useState, useRef, useEffect } from "react";
import { useNavigate, useLocation } from 'react-router-dom';
import "./About.css";
import axios from 'axios';
const DragDropFiles = ({ 
  handleFile, 
  processedImage, 
  clearProcessedImage, 
  isUploaded, 
  setIsUploaded, 
  files,  // Add files here
  setFiles  // Add setFiles here
}) => {
  const [displayImage, setDisplayImage] = useState(processedImage);
  const inputRef = useRef();
  const location = useLocation();
  const navigate = useNavigate();

    useEffect(() => {
      const params = new URLSearchParams(location.search);
      const redirected = params.get('redirected');
      console.log('Redirected:', redirected);  // Log the redirected value
  
      // If not redirected, reset states
      if (redirected !== 'true') {
          setFiles(null);
          setIsUploaded(false);
          handleCancel();
          setDisplayImage(null);
          handleFile(null, false);
          clearProcessedImage();
          if (inputRef.current) {
              inputRef.current.value = '';  // Reset the input element's value
          }
      }
  }, [location.search]);  // Add location.search as a dependency
  

    useEffect(() => {
        setDisplayImage(processedImage || null);
    }, [processedImage]);

    const handleDragOver = (event) => {
        event.preventDefault();
    };

    const handleDrop = async (event) => {
        event.preventDefault();
        if (files || isUploaded) {
          handleCancel(); // Clear existing file before setting new
        }
        setDisplayImage(URL.createObjectURL(event.dataTransfer.files[0]));
        setFiles(event.dataTransfer.files);
        setIsUploaded(true);
        await handleUpload(event.dataTransfer.files);
      };
    
    const handleSelect = async (event) => {
        event.preventDefault();
        if (files || isUploaded) {
          handleCancel(); // Clear existing file before setting new
        }
        setDisplayImage(URL.createObjectURL(event.target.files[0]));
        setFiles(event.target.files);
        setIsUploaded(true);
        await handleUpload(event.target.files);
      };
    
  
  // ... rest of your code
  
  const handleUpload = async (files) => {
    if (!files || files.length === 0) {
        console.error('No files to upload.');
        return;
    }

    // Clear previous image content in Redis before uploading the new image
    try {
        await axios.post("http://localhost:5001/clear-image-content");
        console.log("Cleared previous image content from Redis");
    } catch (error) {
        console.error("Failed to clear previous image content from Redis:", error);
    }

    const formData = new FormData();
    formData.append("file", files[0]);
    try {
        await axios.post("http://localhost:5001/upload-image", formData, {
            headers: { "Content-Type": "multipart/form-data" },
        });
        handleFile(files, true);
        console.log("Uploaded new image and processed content");
    } catch (error) {
        console.error("Failed to upload image:", error);
    }
};
  

    const handleCancel = async () => {
        // Clear the current image and extracted content
        console.log("Handle cancel just called");
        try {
            await axios.post("http://localhost:5001/clear-image-content");
            console.log("Cleared current image content from Redis");
        } catch (error) {
            console.error("Failed to clear current image content from Redis:", error);
        }

        setFiles(null);
        setIsUploaded(false); // Clear the displayed image
        handleFile(null, false);
        setDisplayImage(null);
        clearProcessedImage(); // Clear processedImage in parent component
        if (inputRef.current) {
            inputRef.current.value = ''; // Reset the input element's value
        }

        const params = new URLSearchParams(location.search);
        params.delete('redirected');
        navigate({
            pathname: location.pathname,
            search: params.toString()
        });
    };

    if (files || isUploaded || processedImage) {
        return (
            <>
                <div className="dropzone">
                    <img src={displayImage} className="uploaded-img" alt="Uploaded or processed" />
                </div>
                {(files || processedImage) && (
                    <>
                        <div className="actions">
                            <button className="dropzone-button2" onClick={handleCancel}>Remove Image</button>
                        </div>
                    </>
                )}
            </>
        );
    }

    return (
        <>
            <div className="dropzone" onDragOver={handleDragOver} onDrop={handleDrop}>
                <h4>Utilize InsightAI's Chrome extension for easy screenshots, or upload image directly from your computer</h4>
                <br></br>
                <br></br>
                <h5>We currently *ONLY* support images containing math equations, chemical equations, computer code snippets, or plain text.</h5>
                <br></br>
                <br></br>
                <input
                    type="file"
                    onChange={handleSelect}
                    hidden
                    accept="image/png, image/jpeg"
                    ref={inputRef}
                />
                <button onClick={() => inputRef.current.click()} className="dropzone-button">
                    Upload Image
                </button>
            </div>
            <div className="actions"></div>
        </>
    );
};

export default DragDropFiles;