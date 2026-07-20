import { useState, useRef, useEffect } from 'react'
import axios from 'axios'
import { FiSend, FiChevronDown, FiChevronUp, FiCopy, FiCheck } from 'react-icons/fi'
import { VscFilePdf } from 'react-icons/vsc'
import ReactMarkdown from 'react-markdown'
import './index.css'

function App() {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'ai',
      text: 'नमस्कार! मी तुमचा AI असिस्टंट आहे. तुम्ही मला कोणतेही प्रश्न विचारू शकता, आणि मी तुम्हाला मराठीत उत्तर देईन.'
    }
  ])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!inputValue.trim()) return

    const userMessage = {
      id: Date.now(),
      type: 'user',
      text: inputValue
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await axios.post(`${apiUrl}/api/search`, {
        query: userMessage.text
      })

      const aiMessage = {
        id: Date.now() + 1,
        type: 'ai',
        text: response.data.answer,
        sources: response.data.context
      }

      setMessages(prev => [...prev, aiMessage])
    } catch (error) {
      // Check if it's a 429 Quota Error from the backend
      const errorMsg = error.response?.data?.detail || '';
      let displayError = 'माफ करा, काही तांत्रिक अडचण आली आहे. (Error connecting to AI Server)';
      
      if (errorMsg.includes('429') || errorMsg.includes('quota')) {
        displayError = 'माफ करा, AI ची मर्यादा (Quota Limit) संपली आहे. कृपया 1 मिनिट थांबा आणि पुन्हा प्रयत्न करा.';
      }
      
      const errorMessage = {
        id: Date.now() + 1,
        type: 'ai',
        text: displayError
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <VscFilePdf size={28} color="#60a5fa" />
        <h1>Private PDF Search</h1>
      </header>

      <main className="chat-container">
        {messages.map((msg) => (
          <div key={msg.id} className={`message ${msg.type}`}>
            <div className="message-content">
              {msg.type === 'ai' ? (
                <div className="markdown-content">
                  <ReactMarkdown>{msg.text}</ReactMarkdown>
                </div>
              ) : (
                msg.text
              )}
              
              {msg.sources && msg.sources.length > 0 && (
                <SourceDropdown sources={msg.sources} />
              )}
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="message ai">
            <div className="message-content">
              <div className="typing-indicator">
                <div className="typing-dot"></div>
                <div className="typing-dot"></div>
                <div className="typing-dot"></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </main>

      <div className="input-area">
        <div className="input-wrapper">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="येथे तुमचा प्रश्न लिहा... (Press Enter to send)"
            rows="1"
          />
        </div>
        <button 
          className="send-button" 
          onClick={handleSend}
          disabled={!inputValue.trim() || isLoading}
        >
          <FiSend size={22} />
        </button>
      </div>
    </div>
  )
}

function SourceDropdown({ sources }) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <div className="sources-container">
      <div className="sources-header" onClick={() => setIsOpen(!isOpen)}>
        <span>संदर्भ पहा (View References)</span>
        {isOpen ? <FiChevronUp /> : <FiChevronDown />}
      </div>
      {isOpen && (
        <div className="sources-body">
          {sources.map((source, index) => (
            <SourceCard key={index} source={source} index={index} />
          ))}
        </div>
      )}
    </div>
  )
}

function SourceCard({ source, index }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(source.text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const bookName = source.metadata?.book_name || 'Unknown Book';
  const pageNum = source.metadata?.page_number || 'Unknown';

  return (
    <div className="source-item">
      <div className="source-meta">
        <span className="source-badge">📖 {bookName}</span>
        <span className="source-badge">📄 Page {pageNum}</span>
        <button className="copy-btn" onClick={handleCopy} title="Copy Transcript">
          {copied ? <FiCheck size={14} color="#10b981" /> : <FiCopy size={14} />}
          <span>{copied ? 'Copied!' : 'Copy Transcript'}</span>
        </button>
      </div>
      <div className="source-text">{source.text}</div>
    </div>
  )
}

export default App
