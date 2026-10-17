import React, { useState } from 'react';
import { Sparkles, Send, HelpCircle, Bot, Cpu } from 'lucide-react';
import { askAgent } from '../services/api';
import TracePanel from './TracePanel';

const EXAMPLE_QUESTIONS = [
  'Which websites use chat-widget.js?',
  'What is the blast radius if cdn-demo.netlify.app is compromised?',
  'Show the load chain from https://bakery-demo.netlify.app/ to helper.js',
  'What are the single points of failure across all client sites?',
  'Who maintains https://bakery-demo.netlify.app?',
];

export default function AskBox() {
  const [question, setQuestion] = useState('Which websites use chat-widget.js?');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);

  const handleAsk = async (qToAsk) => {
    const query = qToAsk || question;
    if (!query.trim()) return;

    setLoading(true);
    try {
      const res = await askAgent(query);
      setResponse(res);
    } catch (err) {
      console.error('Ask error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleAsk();
    }
  };

  return (
    <div className="ask-section">
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <Sparkles size={18} color="#2563eb" />
            <span>Blast Radius AI Security Agent</span>
          </div>
          <span style={{ fontSize: '13px', color: '#64748b' }}>
            FalkorDB Graph Knowledge + Gemini Function Calling
          </span>
        </div>

        <div className="card-body">
          {/* Question Input */}
          <div className="ask-input-group">
            <input
              type="text"
              className="ask-input"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about scripts, blast radius, owners, or single points of failure..."
              disabled={loading}
            />
            <button
              className="btn btn-primary"
              onClick={() => handleAsk()}
              disabled={loading || !question.trim()}
              style={{ minWidth: '120px', justifyContent: 'center' }}
            >
              {loading ? (
                <span>Thinking...</span>
              ) : (
                <>
                  <Send size={15} /> Ask
                </>
              )}
            </button>
          </div>

          {/* Quick Examples */}
          <div style={{ marginBottom: '20px' }}>
            <span style={{ fontSize: '12px', color: '#64748b', fontWeight: 600, display: 'block', marginBottom: '8px' }}>
              Suggested Inquiries:
            </span>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {EXAMPLE_QUESTIONS.map((eq, i) => (
                <button
                  key={i}
                  className="btn btn-outline"
                  onClick={() => {
                    setQuestion(eq);
                    handleAsk(eq);
                  }}
                  style={{ fontSize: '12px', padding: '4px 10px', height: 'auto' }}
                  disabled={loading}
                >
                  <HelpCircle size={12} color="#64748b" /> {eq}
                </button>
              ))}
            </div>
          </div>

          {/* Answer Display */}
          {response && (
            <div className="ask-answer-box">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <span className="ask-answer-title" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Bot size={16} color="#2563eb" /> Agent Response
                </span>
                {response.used_ai ? (
                  <span className="badge-runtime-only" style={{ background: '#eff6ff', color: '#1d4ed8', borderColor: '#bfdbfe' }}>
                    <Sparkles size={11} /> AI Reasoning (Gemini Flash-Lite)
                  </span>
                ) : (
                  <span className="badge-html-direct" style={{ fontSize: '11px' }}>
                    <Cpu size={11} /> Rules Engine / Deterministic Fallback
                  </span>
                )}
              </div>

              <p className="ask-answer-text">
                {response.answer}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Trace Out */}
      {response && response.trace && (
        <TracePanel trace={response.trace} />
      )}
    </div>
  );
}
