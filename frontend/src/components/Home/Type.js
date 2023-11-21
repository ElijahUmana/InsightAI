import React from "react";
import Typewriter from "typewriter-effect";
import "./Type.css";

function Type() {
  return (
    <Typewriter
      className="typewriter"
      options={{
        strings: [
          "Follow  your  curiosity",
          "Interact with a personal tutor just like a normal convo",
          "Gain explanations tailored just for you!",
        ],
        autoStart: true,
        loop: true,
        deleteSpeed: 50,
      }}
      style={{ border: "1px solid red" }}
    />
  );
}

export default Type;
