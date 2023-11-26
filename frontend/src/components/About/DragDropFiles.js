import { useState, useRef, useEffect } from "react";
import { useLocation } from "react-router-dom";  // Import useLocation
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

    useEffect(() => {
      const params = new URLSearchParams(location.search);
      const redirected = params.get('redirected');
      console.log('Redirected:', redirected);  // Log the redirected value
  
      // If not redirected, reset states
      if (redirected !== 'true') {
          setFiles(null);
          setIsUploaded(false);
          setDisplayImage(null);
          handleFile(null, false);
          clearProcessedImage();
          if (inputRef.current) {
              inputRef.current.value = '';  // Reset the input element's value
          }
      }
    }, [location.search, setFiles, setIsUploaded, handleFile, clearProcessedImage]);
  

    useEffect(() => {
        if (processedImage) {
            setDisplayImage(processedImage);
        }
    }, [processedImage]);
    

    const handleDragOver = (event) => {
        event.preventDefault();
    };

    const handleDrop = async (event) => {
      event.preventDefault();
      const imageUrl = URL.createObjectURL(event.dataTransfer.files[0]);
      setDisplayImage(imageUrl);
      setFiles(event.dataTransfer.files);
      setIsUploaded(true);
      await handleUpload(event.dataTransfer.files);  // Automatically upload the file
  };
  
  const handleSelect = async (event) => {
      event.preventDefault();
      const imageUrl = URL.createObjectURL(event.target.files[0]);
      setDisplayImage(imageUrl);
      setFiles(event.target.files);
      setIsUploaded(true);
      await handleUpload(event.target.files);  // Automatically upload the file
  };
  
  
  const handleUpload = async (files) => {
      if (!files || files.length === 0) {
          console.error('No files to upload.');
          return;
      }
  
      const formData = new FormData();
      formData.append("file", files[0]);
      try {
          await axios.post("https://insightai-backend-c99c36a74d36.herokuapp.com/upload-image", formData, {
              headers: { "Content-Type": "multipart/form-data" },
          });
          handleFile(files, true);
      } catch (error) {
          console.error("Failed to upload image to Flask:", error);
      }
  };
  

    const handleCancel = () => {
        setFiles(null);
        setIsUploaded(false);  // Clear the displayed image
        handleFile(null, false);
        clearProcessedImage();  // Clear processedImage in About
        if (inputRef.current) {
            inputRef.current.value = '';  // Reset the input element's value
        }
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
            {displayImage ? (
                // If displayImage is set, show the image and the Remove Image button
                <div className="dropzone">
                    <img src={displayImage} className="uploaded-img" alt="Uploaded or processed" />
                    <div className="actions">
                        <button className="dropzone-button2" onClick={handleCancel}>Remove Image</button>
                    </div>
                </div>
            ) : (
                // If no image is set, show the upload interface
                <div className="dropzone" onDragOver={handleDragOver} onDrop={handleDrop}>
                    <h4>Utilize InsightAI's Chrome extension for easy screenshots, or upload image directly from your computer</h4>
                    <br></br>
                    <h5>We currently *ONLY* support images containing math equations, chemical equations, computer code snippets, or plain text.</h5>
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
            )}
            <div className="actions"></div>
        </>
    );
    
};

export default DragDropFiles;
