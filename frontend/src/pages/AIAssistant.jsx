import React, { useState, useRef, useEffect } from 'react';
import { Bot, Send, Loader2, Sparkles, AlertTriangle, CheckCircle2, X } from 'lucide-react';
import api from '../services/api';
import DisclaimerModal from '../components/DisclaimerModal';

export default function AIAssistant() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "Hello! I'm ERIK, your AI assistant. I can help you with:\n\n✓ Analyzing financial reports\n✓ Understanding Zambian compliance (PAYE, NAPSA, NHIMA)\n✓ Business insights and recommendations\n✓ Navigating the ERP system\n\nHow can I assist you today?",
      timestamp: new Date().toISOString()
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [showDisclaimer, setShowDisclaimer] = useState(false);
  const [disclaimerAccepted, setDisclaimerAccepted] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Show disclaimer on first visit
    const hasSeenDisclaimer = localStorage.getItem('ai_disclaimer_accepted');
    if (!hasSeenDisclaimer) {
      setShowDisclaimer(true);
    } else {
      setDisclaimerAccepted(true);
    }
  }, []);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || loading) return;

    if (!disclaimerAccepted) {
      setShowDisclaimer(true);
      return;
    }

    const userMessage = inputMessage.trim();
    setInputMessage('');

    // Add user message
    const newUserMessage = {
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, newUserMessage]);
    setLoading(true);

    try {
      // Prepare conversation history
      const conversationHistory = messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      // Call AI API
      const response = await api.post('/api/ai/chat', {
        message: userMessage,
        conversation_history: conversationHistory
      });

      if (response.data.success) {
        const assistantMessage = {
          role: 'assistant',
          content: response.data.response,
          timestamp: response.data.timestamp,
          tokens: response.data.tokens_used
        };
        setMessages(prev => [...prev, assistantMessage]);
      } else {
        const errorMessage = {
          role: 'assistant',
          content: `⚠️ ${response.data.response}`,
          timestamp: new Date().toISOString(),
          isError: true
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      const errorMessage = {
        role: 'assistant',
        content: '⚠️ Sorry, I encountered an error. Please try again or contact support if the issue persists.',
        timestamp: new Date().toISOString(),
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const quickActions = [
    { text: "Explain PAYE calculation", action: "Explain how PAYE is calculated in Zambia" },
    { text: "Analyze cash flow", action: "Analyze my company's cash flow and provide insights" },
    { text: "NAPSA compliance", action: "Explain NAPSA compliance requirements" },
    { text: "Inventory tips", action: "Give me tips for better inventory management" }
  ];

  const handleQuickAction = (action) => {
    setInputMessage(action);
  };

  const handleAcceptDisclaimer = () => {
    localStorage.setItem('ai_disclaimer_accepted', 'true');
    setDisclaimerAccepted(true);
  };

  const formatMessage = (content) => {
    // Convert markdown-style formatting to HTML
    return content
      .split('\n')
      .map((line, i) => {
        // Headers
        if (line.startsWith('###')) {
          return <h4 key={i} className="text-lg font-semibold text-white mt-4 mb-2">{line.replace(/^###\s*/, '')}</h4>;
        }
        if (line.startsWith('##')) {
          return <h3 key={i} className="text-xl font-semibold text-white mt-4 mb-2">{line.replace(/^##\s*/, '')}</h3>;
        }
        // Bold text
        if (line.includes('**')) {
          const parts = line.split('**');
          return (
            <p key={i} className="mb-2">
              {parts.map((part, j) => 
                j % 2 === 0 ? part : <strong key={j} className="font-semibold text-emerald-400">{part}</strong>
              )}
            </p>
          );
        }
        // Bullet points
        if (line.trim().startsWith('✓') || line.trim().startsWith('-') || line.trim().startsWith('•')) {
          return <li key={i} className="ml-6 mb-1">{line.replace(/^[✓\-•]\s*/, '')}</li>;
        }
        // Regular text
        if (line.trim()) {
          return <p key={i} className="mb-2">{line}</p>;
        }
        return <br key={i} />;
      });
  };

  return (
    <div className="flex flex-col h-full">
      <DisclaimerModal
        isOpen={showDisclaimer}
        onClose={() => setShowDisclaimer(false)}
        onAccept={handleAcceptDisclaimer}
        type="ai"
      />

      {/* Header */}
      <div className="flex items-center justify-between p-6 border-b border-white/10">
        <div className="flex items-center space-x-3">
          <div className="p-3 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-500">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">ERIK AI Assistant</h1>
            <p className="text-sm text-gray-400">Powered by Claude Sonnet 4.5</p>
          </div>
        </div>
        {!disclaimerAccepted && (
          <button
            onClick={() => setShowDisclaimer(true)}
            className="flex items-center space-x-2 px-4 py-2 bg-yellow-500/20 hover:bg-yellow-500/30 text-yellow-400 rounded-lg transition-colors text-sm"
          >
            <AlertTriangle className="w-4 h-4" />
            <span>View AI Disclaimer</span>
          </button>
        )}
      </div>

      {/* Quick Actions */}
      {messages.length === 1 && (
        <div className="p-6 border-b border-white/10">
          <p className="text-sm text-gray-400 mb-3">Quick actions:</p>
          <div className="grid grid-cols-2 gap-3">
            {quickActions.map((action, idx) => (
              <button
                key={idx}
                onClick={() => handleQuickAction(action.action)}
                className="p-3 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-left transition-colors"
              >
                <p className="text-sm text-gray-300">{action.text}</p>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.map((message, idx) => (
          <div
            key={idx}
            className={`flex items-start space-x-3 ${
              message.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''
            }`}
          >
            <div
              className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center ${
                message.role === 'user'
                  ? 'bg-blue-500'
                  : message.isError
                  ? 'bg-red-500'
                  : 'bg-gradient-to-br from-emerald-500 to-teal-500'
              }`}
            >
              {message.role === 'user' ? (
                <span className="text-white font-semibold">U</span>
              ) : message.isError ? (
                <AlertTriangle className="w-5 h-5 text-white" />
              ) : (
                <Bot className="w-5 h-5 text-white" />
              )}
            </div>

            <div
              className={`flex-1 max-w-3xl ${
                message.role === 'user' ? 'text-right' : ''
              }`}
            >
              <div
                className={`inline-block p-4 rounded-2xl ${
                  message.role === 'user'
                    ? 'bg-blue-500 text-white'
                    : message.isError
                    ? 'bg-red-500/20 border border-red-500/30 text-red-200'
                    : 'bg-white/5 border border-white/10 text-gray-300'
                }`}
              >
                <div className="text-sm whitespace-pre-wrap">
                  {message.role === 'user' ? message.content : formatMessage(message.content)}
                </div>
              </div>
              <p className="text-xs text-gray-500 mt-1 px-2">
                {new Date(message.timestamp).toLocaleTimeString()}
                {message.tokens && (
                  <span className="ml-2">• {message.tokens} tokens</span>
                )}
              </p>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div className="flex-1 max-w-3xl">
              <div className="inline-block p-4 rounded-2xl bg-white/5 border border-white/10">
                <div className="flex items-center space-x-2">
                  <Loader2 className="w-4 h-4 text-emerald-400 animate-spin" />
                  <span className="text-sm text-gray-400">ERIK is thinking...</span>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-6 border-t border-white/10">
        <form onSubmit={handleSendMessage} className="flex items-end space-x-3">
          <div className="flex-1">
            <textarea
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage(e);
                }
              }}
              placeholder="Ask me anything about your business..."
              rows="1"
              className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 resize-none"
              style={{ minHeight: '48px', maxHeight: '120px' }}
            />
          </div>
          <button
            type="submit"
            disabled={!inputMessage.trim() || loading}
            className="p-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {loading ? (
              <Loader2 className="w-6 h-6 text-white animate-spin" />
            ) : (
              <Send className="w-6 h-6 text-white" />
            )}
          </button>
        </form>
        <p className="text-xs text-gray-500 mt-2 text-center">
          Press Enter to send • Shift+Enter for new line • AI responses should always be verified
        </p>
      </div>
    </div>
  );
}
