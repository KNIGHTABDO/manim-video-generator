import React, { useState } from 'react';

function App() {
  const [concept, setConcept] = useState('');
  const [videoUrl, setVideoUrl] = useState('');
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [chatMsg, setChatMsg] = useState('');
  const [chatResp, setChatResp] = useState('');
  const [chatLoading, setChatLoading] = useState(false);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setVideoUrl('');
    setCode('');
    const res = await fetch('/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ concept })
    });
    const data = await res.json();
    if (data.success) {
      setVideoUrl(data.video_url);
      setCode(data.code);
    }
    setLoading(false);
  };

  const handleChat = async (e: React.FormEvent) => {
    e.preventDefault();
    setChatLoading(true);
    setChatResp('');
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: chatMsg })
    });
    const data = await res.json();
    if (data.success) setChatResp(data.response);
    setChatLoading(false);
  };

  return (
    <div style={{ maxWidth: 700, margin: '40px auto', fontFamily: 'sans-serif' }}>
      <h1>Manim Video Generator</h1>
      <form onSubmit={handleGenerate} style={{ marginBottom: 30 }}>
        <input
          value={concept}
          onChange={e => setConcept(e.target.value)}
          placeholder="Enter math concept (e.g. Pythagorean theorem)"
          style={{ width: '70%', padding: 8, fontSize: 16 }}
        />
        <button type="submit" style={{ padding: 10, fontSize: 16, marginLeft: 10 }} disabled={loading}>
          {loading ? 'Generating...' : 'Generate Video'}
        </button>
      </form>
      {videoUrl && (
        <div style={{ marginBottom: 20 }}>
          <video src={videoUrl} controls style={{ width: '100%' }} />
        </div>
      )}
      {code && (
        <pre style={{ background: '#222', color: '#fff', padding: 16, borderRadius: 8, overflowX: 'auto' }}>{code}</pre>
      )}
      <hr style={{ margin: '40px 0' }} />
      <h2>Math Chat</h2>
      <form onSubmit={handleChat} style={{ marginBottom: 20 }}>
        <input
          value={chatMsg}
          onChange={e => setChatMsg(e.target.value)}
          placeholder="Ask a math question..."
          style={{ width: '70%', padding: 8, fontSize: 16 }}
        />
        <button type="submit" style={{ padding: 10, fontSize: 16, marginLeft: 10 }} disabled={chatLoading}>
          {chatLoading ? 'Sending...' : 'Send'}
        </button>
      </form>
      {chatResp && (
        <div style={{ background: '#f5f5f5', padding: 16, borderRadius: 8 }}>{chatResp}</div>
      )}
    </div>
  );
}

export default App;
