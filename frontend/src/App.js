import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, BarChart3, Clock, MessageSquare, Zap, CheckCircle, AlertCircle, Loader, Plus, Menu, X, History } from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000';

// Markdown formatter function
const formatMarkdown = (text) => {
  if (!text) return '';
  
  // Bold text: **text** or __text__
  let formatted = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  formatted = formatted.replace(/__(.+?)__/g, '<strong>$1</strong>');
  
  // Italic text: *text* or _text_
  formatted = formatted.replace(/\*(.+?)\*/g, '<em>$1</em>');
  formatted = formatted.replace(/_(.+?)_/g, '<em>$1</em>');
  
  // Bullet points: * item or - item
  formatted = formatted.replace(/^\* (.+)$/gm, '<li>$1</li>');
  formatted = formatted.replace(/^- (.+)$/gm, '<li>$1</li>');
  
  // Wrap consecutive <li> items in <ul>
  formatted = formatted.replace(/(<li>.*<\/li>\n?)+/g, (match) => `<ul>${match}</ul>`);
  
  // Line breaks
  formatted = formatted.replace(/\n\n/g, '<br/><br/>');
  formatted = formatted.replace(/\n/g, '<br/>');
  
  return formatted;
};

function App() {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(() => {
    const stored = localStorage.getItem('session_id');
    return stored || `session-${Date.now()}`;
  });
  const [stats, setStats] = useState(null);
  const [sessionStats, setSessionStats] = useState({ conversations: 0, avgResponseTime: 0 });
  const [requestStartTime, setRequestStartTime] = useState(null);
  const [savedConversations, setSavedConversations] = useState(() => {
    const saved = localStorage.getItem('saved_conversations');
    return saved ? JSON.parse(saved) : [];
  });
  const [currentConversationTitle, setCurrentConversationTitle] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    localStorage.setItem('session_id', sessionId);
    fetchStats();
    setSessionStats({ conversations: 0, avgResponseTime: 0 });
  }, [sessionId]);

  useEffect(() => {
    // Save conversations to localStorage whenever they change
    localStorage.setItem('saved_conversations', JSON.stringify(savedConversations));
  }, [savedConversations]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/conversations/stats`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const saveCurrentConversation = () => {
    if (messages.length === 0) return;

    // Find if conversation with this sessionId already exists
    const existingIndex = savedConversations.findIndex(conv => conv.id === sessionId);
    
    const conversationData = {
      id: sessionId,
      title: currentConversationTitle || messages[0]?.content.substring(0, 50) || 'New Conversation',
      messages: messages,
      timestamp: new Date().toISOString(),
      messageCount: messages.length
    };

    if (existingIndex >= 0) {
      // Update existing conversation
      const updated = [...savedConversations];
      updated[existingIndex] = conversationData;
      setSavedConversations(updated);
    } else {
      // Add new conversation
      setSavedConversations(prev => [conversationData, ...prev]);
    }
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = {
      role: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);
    
    const startTime = Date.now();
    setRequestStartTime(startTime);

    try {
      const history = messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: inputMessage,
          history: history,
          session_id: sessionId
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to get response');
      }

      const data = await response.json();
      
      const endTime = Date.now();
      const responseTime = endTime - startTime;
      
      const assistantMessage = {
        role: 'assistant',
        content: data.response,
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, assistantMessage]);
      
      // Set conversation title from first user message
      if (messages.length === 0 && !currentConversationTitle) {
        setCurrentConversationTitle(inputMessage.substring(0, 50));
      }
      
      setSessionStats(prev => ({
        conversations: prev.conversations + 1,
        avgResponseTime: prev.conversations === 0 
          ? responseTime 
          : Math.round((prev.avgResponseTime * prev.conversations + responseTime) / (prev.conversations + 1))
      }));
      
      fetchStats();
      
      // Save conversation after each exchange
      setTimeout(() => saveCurrentConversation(), 100);
    } catch (error) {
      console.error('Error:', error);
      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date().toISOString(),
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const formatResponseTime = (ms) => {
    if (ms < 1000) {
      return `${ms}ms`;
    } else if (ms < 60000) {
      return `${(ms / 1000).toFixed(1)}s`;
    } else {
      return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
    }
  };

  const handleNewChat = () => {
    // Save current conversation before starting new one
    saveCurrentConversation();
    
    const newSessionId = `session-${Date.now()}`;
    setSessionId(newSessionId);
    localStorage.setItem('session_id', newSessionId);
    setMessages([]);
    setCurrentConversationTitle('');
    setSessionStats({ conversations: 0, avgResponseTime: 0 });
    inputRef.current?.focus();
  };

  const handleLoadConversation = (conv) => {
    // Save current conversation before loading another
    if (messages.length > 0) {
      saveCurrentConversation();
    }
    
    setSessionId(conv.id);
    localStorage.setItem('session_id', conv.id);
    setMessages(conv.messages);
    setCurrentConversationTitle(conv.title);
    setSessionStats({ conversations: conv.messages.filter(m => m.role === 'assistant').length, avgResponseTime: 0 });
  };

  const handleDeleteConversation = (convId, e) => {
    e.stopPropagation(); // Prevent loading the conversation when clicking delete
    setSavedConversations(prev => prev.filter(conv => conv.id !== convId));
    
    // If deleting current conversation, start new chat
    if (convId === sessionId) {
      handleNewChat();
    }
  };

  const handleClearAllConversations = () => {
    if (window.confirm('Are you sure you want to delete all conversation history? This cannot be undone.')) {
      setSavedConversations([]);
      localStorage.removeItem('saved_conversations');
      handleNewChat();
    }
  };

  const quickActions = [
    { icon: MessageSquare, text: 'Check Ticket Status', query: 'What is the status of ticket T-123?' },
    { icon: Zap, text: 'Reset Password', query: 'I need to reset my password for john.doe@example.com' },
    { icon: CheckCircle, text: 'Reset Dashboard Metrics', query: 'How do I reset my dashboard metrics?' },
    { icon: AlertCircle, text: 'Billing Question', query: 'How to get billing information?' }
  ];  

  const handleQuickAction = (query) => {
    setInputMessage(query);
    inputRef.current?.focus();
  };

  return (
    <div className="app-container" style={styles.appContainer}>
      {/* Sidebar */}
      <div className={`sidebar ${sidebarOpen ? 'open' : 'closed'}`} style={sidebarOpen ? styles.sidebar : styles.sidebarClosed}>
        <div style={styles.sidebarHeader}>
          <button onClick={() => setSidebarOpen(!sidebarOpen)} style={styles.toggleButton} className="toggle-button">
            {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
          {sidebarOpen && <h3 style={styles.sidebarTitle}>Conversations</h3>}
        </div>

        {sidebarOpen && (
          <>
            <button onClick={handleNewChat} style={styles.newChatButton} className="new-chat-button">
              <Plus size={18} />
              New Chat
            </button>

            <div style={styles.conversationsList} className="conversations-list">
              <div style={styles.conversationsHeader}>
                <History size={16} />
                <span>Recent</span>
                {savedConversations.length > 0 && (
                  <button 
                    onClick={handleClearAllConversations} 
                    style={styles.clearAllButton}
                    className="clear-all-button"
                    title="Clear all conversations"
                  >
                    Clear All
                  </button>
                )}
              </div>
              {savedConversations.length === 0 ? (
                <div style={styles.emptyState}>No conversations yet</div>
              ) : (
                savedConversations.map((conv, idx) => (
                  <div
                    key={conv.id}
                    onClick={() => handleLoadConversation(conv)}
                    style={{
                      ...styles.conversationItem,
                      ...(conv.id === sessionId ? styles.conversationItemActive : {})
                    }}
                    className="conversation-item"
                  >
                    <MessageSquare size={14} style={{ flexShrink: 0 }} />
                    <div style={styles.conversationText}>
                      <div style={styles.conversationMessage}>
                        {conv.title}
                      </div>
                      <div style={styles.conversationTime}>
                        {conv.messageCount} messages · {new Date(conv.timestamp).toLocaleDateString()}
                      </div>
                    </div>
                    <button
                      onClick={(e) => handleDeleteConversation(conv.id, e)}
                      style={styles.deleteButton}
                      className="delete-button"
                      title="Delete conversation"
                    >
                      <X size={14} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </>
        )}
      </div>

      {/* Main Content */}
      <div style={styles.mainWrapper}>
        <header style={styles.header}>
          <div style={styles.headerContent}>
            <div style={styles.logoSection}>
              
              <div style={styles.logoIcon}>
                <Sparkles size={28} />
              </div>
              <div style={styles.logoText}>
                <h1 style={styles.logoH1}>Support Intelligence</h1>
                <p style={styles.logoP}>AI-Powered Customer Support</p>
              </div>
            </div>
            
            {stats && (
              <div style={styles.statsBar}>
                {/* <div style={styles.statItem}>
                  <MessageSquare size={18} />
                  <span style={styles.statValue}>{sessionStats.conversations}</span>
                  <label style={styles.statLabel}>Conversations</label>
                </div> */}
                {/* <div style={styles.statItem}>
                  <Clock size={18} />
                  <span style={styles.statValue}>{formatResponseTime(sessionStats.avgResponseTime)}</span>
                  <label style={styles.statLabel}>Avg Response Time</label>
                </div> */}
              </div>
            )}
          </div>
        </header>

        <main style={styles.mainContent}>
          <div style={styles.chatContainer} className="chat-container">
            {messages.length === 0 && (
              <div style={styles.welcomeScreen}>
                <div style={styles.welcomeIcon}>
                  <Bot size={64} />
                </div>
                <h2 style={styles.welcomeH2}>Welcome to Support Intelligence</h2>
                <p style={styles.welcomeP}>Your AI-powered support assistant is ready to help you with tickets, account management, and technical support.</p>

                <div style={styles.quickActions}>
                  <h3 style={styles.quickActionsH3}>Quick Actions</h3>
                  <div style={styles.actionButtons}>
                    {quickActions.map((action, idx) => (
                      <button
                        key={idx}
                        style={styles.actionButton}
                        className="action-button"
                        onClick={() => handleQuickAction(action.query)}
                      >
                        <action.icon size={20} />
                        {action.text}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {messages.length > 0 && (
              <div style={styles.messagesList}>
                {messages.map((message, idx) => (
                  <div
                    key={idx}
                    style={{
                      ...styles.message,
                      ...(message.role === 'user' ? styles.messageUser : styles.messageAssistant),
                      ...(message.isError ? styles.messageError : {})
                    }}
                  >
                    <div style={message.role === 'user' ? styles.avatarUser : styles.avatarAssistant}>
                      {message.role === 'user' ? <User size={20} /> : <Bot size={20} />}
                    </div>
                    <div style={styles.messageContent}>
                      <div style={message.role === 'user' ? styles.messageHeaderUser : styles.messageHeader}>
                        <span style={styles.messageRole}>
                          {message.role === 'user' ? 'You' : 'AI Assistant'}
                        </span>
                        <span style={styles.messageTime}>
                          {new Date(message.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      <div 
                        style={message.role === 'user' ? styles.messageTextUser : styles.messageText}
                        className={message.role === 'user' ? 'message-text-user' : 'message-text'}
                        dangerouslySetInnerHTML={{ __html: formatMarkdown(message.content) }}
                      />
                    </div>
                  </div>
                ))}
                
                {isLoading && (
                  <div style={{ ...styles.message, ...styles.messageAssistant }}>
                    <div style={styles.avatarAssistant}>
                      <Bot size={20} />
                    </div>
                    <div style={styles.messageContent}>
                      <div style={styles.messageHeader}>
                        <span style={styles.messageRole}>AI Assistant</span>
                      </div>
                      <div style={styles.typingIndicator}>
                        <span style={styles.dot}></span>
                        <span style={{ ...styles.dot, animationDelay: '0.2s' }}></span>
                        <span style={{ ...styles.dot, animationDelay: '0.4s' }}></span>
                      </div>
                    </div>
                  </div>
                )}
                
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>
        </main>

        <footer style={styles.inputFooter}>
          <div style={styles.inputContainer}>
            <div style={styles.inputWrapper} className="input-wrapper">
              <input
                ref={inputRef}
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask me anything about your support tickets, account, or features..."
                disabled={isLoading}
                style={styles.messageInput}
              />
              <button
                onClick={handleSendMessage}
                disabled={!inputMessage.trim() || isLoading}
                className="send-button"
                style={{
                  ...styles.sendButton,
                  ...((!inputMessage.trim() || isLoading) ? styles.sendButtonDisabled : {})
                }}
              >
                {isLoading ? <Loader size={20} style={styles.spinner} /> : <Send size={20} />}
              </button>
            </div>
            <div style={styles.footerText}>
              <Sparkles size={14} />
              Powered by Advanced AI • Secure & Private
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}

const styles = {
  appContainer: {
    display: 'flex',
    height: '100vh',
    width: '100%',
    overflow: 'hidden',
    background: 'linear-gradient(135deg, #FFF5F2 0%, #FFFFFF 100%)',
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif"
  },
  sidebar: {
    width: '280px',
    background: '#FFFFFF',
    borderRight: '2px solid #FFE5DB',
    display: 'flex',
    flexDirection: 'column',
    transition: 'all 0.3s ease',
    boxShadow: '2px 0 8px rgba(255, 107, 53, 0.08)'
  },
  sidebarClosed: {
    width: '60px',
    background: '#FFFFFF',
    borderRight: '2px solid #FFE5DB',
    display: 'flex',
    flexDirection: 'column',
    transition: 'all 0.3s ease'
  },
  sidebarHeader: {
    padding: '1.5rem 1rem',
    borderBottom: '1px solid #FFE5DB',
    display: 'flex',
    alignItems: 'center',
    gap: '1rem'
  },
  toggleButton: {
    background: 'transparent',
    border: 'none',
    cursor: 'pointer',
    color: '#FF6B35',
    padding: '0.5rem',
    borderRadius: '8px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'background 0.2s'
  },
  sidebarTitle: {
    fontSize: '1.125rem',
    fontWeight: '600',
    color: '#212121',
    margin: 0
  },
  newChatButton: {
    margin: '1rem',
    padding: '0.75rem 1rem',
    background: 'linear-gradient(135deg, #FF6B35 0%, #FF8C61 100%)',
    color: '#FFFFFF',
    border: 'none',
    borderRadius: '12px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    fontSize: '0.95rem',
    fontWeight: '500',
    transition: 'transform 0.2s, box-shadow 0.2s',
    boxShadow: '0 2px 8px rgba(255, 107, 53, 0.2)'
  },
  conversationsList: {
    flex: 1,
    overflowY: 'auto',
    padding: '0.5rem'
  },
  conversationsHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '0.5rem',
    padding: '0.75rem 1rem',
    fontSize: '0.875rem',
    fontWeight: '600',
    color: '#757575',
    textTransform: 'uppercase',
    letterSpacing: '0.5px'
  },
  clearAllButton: {
    background: 'transparent',
    border: 'none',
    color: '#FF6B35',
    fontSize: '0.75rem',
    fontWeight: '500',
    cursor: 'pointer',
    padding: '0.25rem 0.5rem',
    borderRadius: '4px',
    transition: 'background 0.2s',
    textTransform: 'none'
  },
  emptyState: {
    padding: '2rem 1rem',
    textAlign: 'center',
    color: '#999',
    fontSize: '0.875rem'
  },
  conversationItem: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '0.75rem',
    padding: '0.75rem 1rem',
    margin: '0.25rem 0',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'background 0.2s',
    background: 'transparent',
    position: 'relative'
  },
  conversationItemActive: {
    background: '#FFF5F2',
    borderLeft: '3px solid #FF6B35'
  },
  deleteButton: {
    background: 'transparent',
    border: 'none',
    color: '#999',
    cursor: 'pointer',
    padding: '0.25rem',
    borderRadius: '4px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    opacity: 0,
    transition: 'all 0.2s',
    position: 'absolute',
    right: '0.5rem',
    top: '50%',
    transform: 'translateY(-50%)'
  },
  conversationText: {
    flex: 1,
    minWidth: 0
  },
  conversationMessage: {
    fontSize: '0.875rem',
    color: '#212121',
    marginBottom: '0.25rem',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap'
  },
  conversationTime: {
    fontSize: '0.75rem',
    color: '#999'
  },
  mainWrapper: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden'
  },
  header: {
    background: 'linear-gradient(135deg, #FF6B35 0%, #E5522E 100%)',
    color: '#FFFFFF',
    padding: '1.5rem 2rem',
    boxShadow: '0 4px 12px rgba(255, 107, 53, 0.2)'
  },
  headerContent: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    maxWidth: '1400px',
    margin: '0 auto'
  },
  logoSection: {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem'
  },
  menuButton: {
    background: 'rgba(255, 255, 255, 0.2)',
    border: 'none',
    padding: '0.5rem',
    borderRadius: '8px',
    color: '#FFFFFF',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center'
  },
  logoIcon: {
    background: 'rgba(255, 255, 255, 0.2)',
    backdropFilter: 'blur(10px)',
    padding: '0.75rem',
    borderRadius: '12px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  },
  logoText: {},
  logoH1: {
    fontSize: '1.75rem',
    fontWeight: '700',
    letterSpacing: '-0.5px',
    marginBottom: '0.25rem',
    margin: 0
  },
  logoP: {
    fontSize: '0.875rem',
    opacity: 0.9,
    margin: 0
  },
  statsBar: {
    display: 'flex',
    gap: '2rem'
  },
  statItem: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '0.25rem',
    background: 'rgba(255, 255, 255, 0.15)',
    backdropFilter: 'blur(10px)',
    padding: '0.75rem 1.5rem',
    borderRadius: '12px',
    border: '1px solid rgba(255, 255, 255, 0.2)'
  },
  statValue: {
    fontSize: '1.5rem',
    fontWeight: '700'
  },
  statLabel: {
    fontSize: '0.75rem',
    opacity: 0.9,
    textTransform: 'uppercase',
    letterSpacing: '0.5px'
  },
  mainContent: {
    flex: 1,
    overflow: 'hidden',
    display: 'flex',
    justifyContent: 'center',
    padding: '2rem'
  },
  chatContainer: {
    width: '100%',
    maxWidth: '1200px',
    height: '100%',
    overflowY: 'auto',
    padding: '0 1rem'
  },
  welcomeScreen: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '3rem 2rem',
    textAlign: 'center'
  },
  welcomeIcon: {
    background: 'linear-gradient(135deg, #FF6B35 0%, #FF8C61 100%)',
    color: '#FFFFFF',
    width: '120px',
    height: '120px',
    borderRadius: '24px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: '2rem',
    boxShadow: '0 8px 24px rgba(255, 107, 53, 0.3)'
  },
  welcomeH2: {
    fontSize: '2.5rem',
    fontWeight: '700',
    color: '#212121',
    marginBottom: '1rem',
    letterSpacing: '-1px'
  },
  welcomeP: {
    fontSize: '1.125rem',
    color: '#757575',
    marginBottom: '3rem',
    maxWidth: '600px'
  },
  quickActions: {
    width: '100%',
    maxWidth: '800px',
    marginTop: '3rem'
  },
  quickActionsH3: {
    fontSize: '1.5rem',
    fontWeight: '600',
    marginBottom: '1.5rem',
    color: '#212121'
  },
  actionButtons: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '1rem'
  },
  actionButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    padding: '1rem 1.5rem',
    background: '#FFFFFF',
    border: '2px solid #FFB399',
    borderRadius: '12px',
    color: '#FF6B35',
    fontSize: '0.95rem',
    fontWeight: '500',
    cursor: 'pointer',
    transition: 'all 0.3s'
  },
  messagesList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1.5rem',
    padding: '2rem 0'
  },
  message: {
    display: 'flex',
    gap: '1rem',
    alignItems: 'flex-start'
  },
  messageUser: {
    flexDirection: 'row-reverse'
  },
  messageAssistant: {},
  messageError: {},
  avatarUser: {
    flexShrink: 0,
    width: '40px',
    height: '40px',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'linear-gradient(135deg, #FF6B35 0%, #FF8C61 100%)',
    color: '#FFFFFF',
    boxShadow: '0 2px 8px rgba(255, 107, 53, 0.2)'
  },
  avatarAssistant: {
    flexShrink: 0,
    width: '40px',
    height: '40px',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: '#FFFFFF',
    border: '2px solid #FFB399',
    color: '#FF6B35'
  },
  messageContent: {
    flex: 1,
    maxWidth: '75%'
  },
  messageHeader: {
    display: 'flex',
    gap: '0.75rem',
    alignItems: 'center',
    marginBottom: '0.5rem'
  },
  messageHeaderUser: {
    display: 'flex',
    gap: '0.75rem',
    alignItems: 'center',
    marginBottom: '0.5rem',
    flexDirection: 'row-reverse'
  },
  messageRole: {
    fontSize: '0.875rem',
    fontWeight: '600',
    color: '#FF6B35'
  },
  messageTime: {
    fontSize: '0.75rem',
    color: '#757575'
  },
  messageText: {
    background: '#FFFFFF',
    padding: '1rem 1.25rem',
    borderRadius: '12px',
    lineHeight: '1.6',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
    border: '1px solid #E0E0E0',
    color: '#212121'
  },
  messageTextUser: {
    background: 'linear-gradient(135deg, #FF6B35 0%, #FF8C61 100%)',
    padding: '1rem 1.25rem',
    borderRadius: '12px',
    lineHeight: '1.6',
    color: '#FFFFFF',
    border: 'none'
  },
  typingIndicator: {
    display: 'flex',
    gap: '0.5rem',
    padding: '1rem'
  },
  dot: {
    width: '8px',
    height: '8px',
    background: '#FF6B35',
    borderRadius: '50%',
    animation: 'bounce 1.4s ease-in-out infinite'
  },
  inputFooter: {
    background: '#FFFFFF',
    borderTop: '2px solid #FFE5DB',
    padding: '1.5rem 2rem',
    boxShadow: '0 -4px 12px rgba(255, 107, 53, 0.08)'
  },
  inputContainer: {
    maxWidth: '1200px',
    margin: '0 auto'
  },
  inputWrapper: {
    display: 'flex',
    gap: '1rem',
    alignItems: 'center',
    background: '#FAFAFA',
    border: '2px solid #E0E0E0',
    borderRadius: '16px',
    padding: '0.5rem',
    marginBottom: '0.75rem'
  },
  messageInput: {
    flex: 1,
    border: 'none',
    background: 'transparent',
    padding: '0.75rem 1rem',
    fontSize: '1rem',
    color: '#212121',
    outline: 'none'
  },
  sendButton: {
    background: 'linear-gradient(135deg, #FF6B35 0%, #FF8C61 100%)',
    color: '#FFFFFF',
    border: 'none',
    width: '48px',
    height: '48px',
    borderRadius: '12px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    transition: 'all 0.3s',
    flexShrink: 0
  },
  sendButtonDisabled: {
    opacity: 0.5,
    cursor: 'not-allowed'
  },
  spinner: {
    animation: 'spin 1s linear infinite'
  },
  footerText: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '0.5rem',
    fontSize: '0.875rem',
    color: '#757575'
  }
};

// Add keyframes for animations
if (!document.getElementById('custom-animations')) {
  const styleSheet = document.createElement("style");
  styleSheet.id = 'custom-animations';
  styleSheet.textContent = `
    @keyframes bounce {
      0%, 60%, 100% { transform: translateY(0); }
      30% { transform: translateY(-10px); }
    }
    @keyframes spin {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }
    
    /* Hover effects */
    .conversation-item:hover {
      background: #FFF5F2 !important;
    }
    
    .conversation-item:hover .delete-button,
    .conversation-item .delete-button:focus {
      opacity: 1;
    }
    
    .delete-button:hover {
      background: #FFE5DB !important;
      color: #FF6B35 !important;
    }
    
    .clear-all-button:hover {
      background: #FFE5DB !important;
    }
    
    .action-button:hover {
      background: #FF6B35 !important;
      color: #FFFFFF !important;
      border-color: #FF6B35 !important;
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(255, 107, 53, 0.3);
    }
    
    .send-button:hover:not(:disabled) {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(255, 107, 53, 0.3);
    }
    
    .send-button:active:not(:disabled) {
      transform: translateY(0);
    }
    
    .new-chat-button:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 16px rgba(255, 107, 53, 0.4) !important;
    }
    
    .toggle-button:hover {
      background: #FFF5F2 !important;
    }
    
    .input-wrapper:focus-within {
      border-color: #FF6B35;
      box-shadow: 0 0 0 4px rgba(255, 107, 53, 0.1);
    }
    
    /* Scrollbar styling */
    .chat-container::-webkit-scrollbar,
    .conversations-list::-webkit-scrollbar {
      width: 8px;
    }
    
    .chat-container::-webkit-scrollbar-track,
    .conversations-list::-webkit-scrollbar-track {
      background: #F5F5F5;
      border-radius: 10px;
    }
    
    .chat-container::-webkit-scrollbar-thumb,
    .conversations-list::-webkit-scrollbar-thumb {
      background: #FFB399;
      border-radius: 10px;
    }
    
    .chat-container::-webkit-scrollbar-thumb:hover,
    .conversations-list::-webkit-scrollbar-thumb:hover {
      background: #FF6B35;
    }
    
    /* Message formatting */
    .message-text ul, .message-text-user ul {
      margin: 0.5rem 0;
      padding-left: 1.5rem;
    }
    
    .message-text li, .message-text-user li {
      margin: 0.25rem 0;
    }
    
    .message-text strong, .message-text-user strong {
      font-weight: 600;
    }
    
    .message-text em, .message-text-user em {
      font-style: italic;
    }
  `;
  document.head.appendChild(styleSheet);
}

export default App;