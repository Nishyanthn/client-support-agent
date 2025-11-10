import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './ChatWindow.css'; // Import the CSS file

function ChatWindow() {
  // State for messages: Array of { role: 'user' | 'assistant', content: string }
  const [messages, setMessages] = useState([]);
  // State for the user's current input
  const [input, setInput] = useState('');
  // State to track loading status
  const [isLoading, setIsLoading] = useState(false);
  // Ref for the message container div to enable auto-scrolling
  const messagesEndRef = useRef(null);

  // Function to scroll to the bottom of the messages container
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Scroll to bottom whenever messages update
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Function to handle sending a message
  const handleSendMessage = async (e) => {
    // Prevent default form submission if used in a form
    if (e) e.preventDefault();

    // Trim the input and check if it's empty
    const userMessageContent = input.trim();
    if (!userMessageContent || isLoading) return; // Don't send empty messages or while loading

    // Add user's message to the state immediately for responsiveness
    const newUserMessage = { role: 'user', content: userMessageContent };
    setMessages(prevMessages => [...prevMessages, newUserMessage]);

    // Clear the input field
    setInput('');
    // Set loading state
    setIsLoading(true);

    // Prepare the history for the API call
    const historyForAPI = messages.map(msg => ({
      role: msg.role,
      content: msg.content
    }));

    try {
      // Make the API call to the backend
      const response = await axios.post('http://127.0.0.1:8000/chat', {
        message: userMessageContent,
        history: historyForAPI
      });

      // Update history based on backend response
       if (response.data && response.data.history) {
        setMessages(response.data.history.map(msg => ({
            role: msg.role.toLowerCase(),
            content: msg.content
        })));
      } else if (response.data && response.data.response) {
         // Fallback if only response is sent
         const assistantResponse = { role: 'assistant', content: response.data.response };
         setMessages(prevMessages => [...prevMessages, assistantResponse]);
      } else {
         console.warn("Received unexpected response structure:", response.data);
         const errorMessage = { role: 'assistant', content: 'Received an empty or unexpected response from the server.' };
         setMessages(prevMessages => [...prevMessages, errorMessage]);
      }

    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' };
      setMessages(prevMessages => [...prevMessages, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-window-wrapper">
      {/* Navbar JSX */}
      <nav className="navbar">
        <div className="navbar-brand">
          {/* Simple Chat Icon */}
          <svg className="navbar-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
            <path fillRule="evenodd" d="M4.804 21.644A6.707 6.707 0 0 0 6 21.75a6.721 6.721 0 0 0 3.583-1.029 1.75 1.75 0 0 0 2.834 0 6.721 6.721 0 0 0 3.583 1.029 6.707 6.707 0 0 0 1.196-.106 1.75 1.75 0 0 0 .33-3.313 10.604 10.604 0 0 1-5.117-4.06 1.75 1.75 0 0 0-3.267 0 10.604 10.604 0 0 1-5.117 4.06 1.75 1.75 0 0 0 .33 3.313Zm7.196-10.375a3 3 0 1 0-5.998-.058 3 3 0 0 0 5.998.058Zm4.5 0a3 3 0 1 0-5.998-.058 3 3 0 0 0 5.998.058Z" clipRule="evenodd" />
          </svg>
          <span className="navbar-title">Client Support Agent</span>
        </div>
        <div className="navbar-links">
          {/* Add links here if needed */}
        </div>
      </nav>
      {/* End of Navbar JSX */}

      {/* Main chat content area */}
      <div className="chat-window-container">
        {/* Message List Area */}
        <div className="message-list">
          {messages.map((msg, index) => (
            <div key={index} className={`message-row ${msg.role === 'user' ? 'user-message-row' : 'assistant-message-row'}`}>
              <div
                className={`message-bubble ${
                  msg.role === 'user'
                    ? 'user-message-bubble'
                    : 'assistant-message-bubble'
                }`}
              >
                {/* Basic Markdown-like formatting for newlines */}
                {msg.content.split('\n').map((line, i, arr) => (
                  <p key={i} className={`message-line ${i === arr.length - 1 ? 'last-line' : ''}`}>{line || '\u00A0'}</p> /* Use non-breaking space for empty lines */
                ))}
              </div>
            </div>
          ))}
          {/* Loading Indicator */}
          {isLoading && (
          <div className="message-row assistant-message-row">
            <div className="message-bubble assistant-message-bubble loading-indicator">
                <div className="loading-dot dot1"></div>
                <div className="loading-dot dot2"></div>
                <div className="loading-dot dot3"></div>
            </div>
          </div>
          )}
          {/* Empty div to mark the end of messages for scrolling */}
          <div ref={messagesEndRef} />
        </div>


        {/* Input Area */}
        <form onSubmit={handleSendMessage} className="input-area">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask your question here..."
            className="chat-input"
            disabled={isLoading} // Disable input while loading
          />
          <button
            type="submit"
            className={`send-button ${isLoading ? 'disabled' : ''}`}
            disabled={isLoading}
            aria-label="Send message"
          >
            {/* Simple Send/Paper Airplane SVG Icon */}
            <svg xmlns="http://www.w3.org/2000/svg" className="send-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </form>
      </div> {/* End chat-window-container */}
    </div> /* End chat-window-wrapper */
  );
}

export default ChatWindow;

