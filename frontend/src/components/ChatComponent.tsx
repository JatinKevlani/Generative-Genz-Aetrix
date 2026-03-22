'use client';
import { useState } from 'react';
import { Send, AlertTriangle } from 'lucide-react';

export default function ChatComponent() {
  const [messages, setMessages] = useState<{role: 'user' | 'ai', content: string}[]>([
    { role: 'ai', content: 'Incident Copilot Active. How can I assist with the current situation?' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    if (!input.trim()) return;
    const userMsg = input.trim();
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query: userMsg })
      });
      const data = await res.json();
      setMessages(prev => [...prev, { role: 'ai', content: data.reply }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'ai', content: 'Error connecting to backend.' }]);
    }
    setLoading(false);
  };

  return (
    <div className="flex flex-col h-full bg-slate-900 rounded-xl shadow-lg border border-slate-800 overflow-hidden">
      <div className="p-4 bg-blue-600 text-white flex items-center gap-2 font-semibold">
        <AlertTriangle size={20} />
        Command Chat
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`p-3 rounded-lg max-w-[85%] text-sm ${
              m.role === 'user' ? 'bg-blue-600 text-white' : 'bg-slate-800 text-slate-300'
            }`}>
              {m.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="p-3 rounded-lg max-w-[80%] text-sm bg-slate-800 text-slate-400 animate-pulse">
              Processing intelligence...
            </div>
          </div>
        )}
      </div>

      <div className="p-3 border-t border-slate-800 flex gap-2">
        <input 
          type="text" 
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Ask for recommendations..." 
          className="flex-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm text-slate-50 placeholder-slate-500"
        />
        <button 
          onClick={sendMessage}
          disabled={loading || !input.trim()}
          className="bg-blue-600 text-white p-2 rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  );
}
