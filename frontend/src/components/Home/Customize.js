import React, { useState } from 'react';
import { Container, Row, Col } from 'react-bootstrap';
import './Customize.css';
import { useNavigate } from 'react-router-dom'; // useNavigate is imported

function Customize() {
  const [text, setText] = useState('');
  const [proceed, setProceed] = useState(false);
  const navigate = useNavigate(); // useNavigate hook

  const handleTextChange = (event) => {
    const newText = event.target.value;
    setText(newText);
    setProceed(newText.length > 20);
  };

  const handleSubmit = async () => {
    if (proceed) {
      // Navigate to the 'about' page immediately
      navigate('/about', { state: { styleText: text } });

      try {
        const response = await fetch('https://insightai-backend-c99c36a74d36.herokuapp.com/onboarding', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ text }),
        });

        const data = await response.json();
        console.log(data);
      } catch (error) {
        console.error('Error:', error);
      }
    }
  };

  return (
    <section>
      <Container fluid className="home-section" id="home">
        <Container className="home-content">
          <Row>
            <Col md={{ span: 6, offset: 3 }} className="home-header">
              <h1 style={{ paddingBottom: 15 }} className="heading">
                <strong className="main-name"> InsightAI </strong> offers a
                customizable experience for every student using Large
                Language Models
                <span className="wave" role="img" aria-label="wave">
                  👩‍💻
                </span>
              </h1>
            </Col>
          </Row>
        </Container>
      </Container>
      <div className="description-container">
        <p className="description">
          Please before getting started briefly respond in one sentence your hobbies/professional experience and your preferred learning style.
          
          IntrinsicAI will use your response as additional context to create better associative chainings and help you
          learn more intuitively!
        </p>
      </div>
      <div className="multi-word-input-container">
        <textarea
          className="multi-word-input"
          placeholder="Enter your prompt"
          value={text}
          onChange={handleTextChange}
        />
        <p> Enter a minimum of 20 characters</p>
      </div>

      {proceed ? (
        <button
          style={{ cursor: 'pointer' }}
          className="started-button"
          onClick={handleSubmit}
        >
          <p style={{ color: 'white' }}>Get Started</p>
        </button>
      ) : (
        <button
          style={{ color: 'white', backgroundColor: 'gray', cursor: 'not-allowed' }}
          className="started-button"
          disabled
        >
          <p>Get Started</p>
        </button>
      )}
    </section>
  );
}

export default Customize;
