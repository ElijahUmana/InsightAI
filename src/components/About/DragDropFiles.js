import { useState, useRef } from "react";
import "./About.css";
import axios from 'axios';


const DragDropFiles = ({ handleFile }) => {
  const [files, setFiles] = useState(null);
  const [isUploaded, setIsUploaded] = useState(false);
  const [imgSrc, setImgSrc] = useState(null);
  const inputRef = useRef();

  const handleDragOver = (event) => {
    event.preventDefault();
  };

  const handleDrop = (event) => {
    event.preventDefault();
    const imageUrl = URL.createObjectURL(event.dataTransfer.files[0]);
    setImgSrc(imageUrl);
    setFiles(event.dataTransfer.files);
    setIsUploaded(true);
  };

  const handleSelect = (event) => {
    event.preventDefault();
    const imageUrl = URL.createObjectURL(event.target.files[0]);
    setImgSrc(imageUrl);
    setFiles(event.target.files);
    setIsUploaded(true);
  };

  // Upload the image and process it immediately on the server side
  const handleUpload = async () => {
    const formData = new FormData();
    formData.append("file", files[0]);
    try {
      const response = await axios.post("http://127.0.0.1:5000/upload-image", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      console.log(response.data.message);
      handleFile(files, true);
    } catch (error) {
      console.error("Failed to upload image to Flask:", error);
    }
  };

  const handleCancel = () => {
    setFiles(null);
    setIsUploaded(false);
    handleFile(null, false);
  };

  if (files) {
    return (
      <>
        <div className="dropzone">
          <img src={imgSrc} className="uploaded-img" />
        </div>
        <ul>
          {Array.from(files).map((file, idx) => (
            <li key={idx}>{file.name}</li>
          ))}
        </ul>
        <div className="actions">
          <button
            className="dropzone-button2"
            onClick={handleCancel}
          >
            Cancel
          </button>
          <button className="dropzone-button2" onClick={handleUpload}>
            Upload
          </button>
        </div>
      </>
    );
  }

  return (
    <>
      <div className="dropzone" onDragOver={handleDragOver} onDrop={handleDrop}>
        <h1>Drag and Drop or Upload a screenshot of what you are trying to learn :) </h1>
        <input
          type="file"
          onChange={handleSelect}
          hidden
          accept="image/png, image/jpeg"
          ref={inputRef}
        />
        <button
          onClick={() => inputRef.current.click()}
          className="dropzone-button"
        >
          Select Files
        </button>
      </div>
      <div className="actions"></div>
    </>
  );
};

export default DragDropFiles;
