'use client';
import { useState, useRef, useCallback } from 'react';
import { Send, AlertTriangle, Mic, MicOff, Volume2, VolumeX, Loader2 } from 'lucide-react';

export default function ChatComponent() {
  const [messages, setMessages] = useState<{role: 'user' | 'ai', content: string}[]>([
    { role: 'ai', content: 'Incident Copilot Active. How can I assist with the current situation?' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useState(true);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const speakText = useCallback((text: string) => {
    if (!ttsEnabled || typeof window === 'undefined') return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.05;
    utterance.pitch = 0.95;
    window.speechSynthesis.speak(utterance);
  }, [ttsEnabled]);

  const sendMessage = async (text?: string) => {
    const userMsg = (text || input).trim();
    if (!userMsg) return;
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: userMsg }),
      });
      const data = await res.json();
      setMessages(prev => [...prev, { role: 'ai', content: data.reply }]);
      speakText(data.reply);
    } catch {
      setMessages(prev => [...prev, { role: 'ai', content: 'Error connecting to backend.' }]);
    }
    setLoading(false);
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm' });
        setTranscribing(true);

        try {
          const formData = new FormData();
          formData.append('audio', audioBlob, 'recording.webm');
          const res = await fetch('http://localhost:8000/api/speech-to-text', {
            method: 'POST',
            body: formData,
          });
          const data = await res.json();
          if (data.transcript) {
            setInput(data.transcript);
            // Auto-send the transcribed message
            await sendMessage(data.transcript);
          }
        } catch {
          console.error('Transcription failed');
        }
        setTranscribing(false);
      };

      mediaRecorder.start();
      setRecording(true);
    } catch {
      console.error('Microphone access denied');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    setRecording(false);
  };

  return (
    <div className="flex flex-col h-full bg-slate-900 rounded-xl shadow-lg border border-slate-800 overflow-hidden">
      <div className="p-4 bg-blue-600 text-white flex items-center gap-2 font-semibold">
        <AlertTriangle size={20} />
        Command Chat
        <div className="ml-auto flex items-center gap-1">
          <button
            onClick={() => {
              setTtsEnabled(!ttsEnabled);
              if (ttsEnabled) window.speechSynthesis.cancel();
            }}
            className="p-1.5 rounded-md hover:bg-blue-500/50 transition-colors"
            title={ttsEnabled ? 'Mute AI voice' : 'Enable AI voice'}
          >
            {ttsEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
          </button>
        </div>
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
        {transcribing && (
          <div className="flex justify-start">
            <div className="p-3 rounded-lg text-sm bg-slate-800 text-blue-400 flex items-center gap-2">
              <Loader2 size={14} className="animate-spin" />
              Transcribing audio...
            </div>
          </div>
        )}
      </div>

      <div className="p-3 border-t border-slate-800 flex gap-2">
        {/* Mic button */}
        <button
          onClick={recording ? stopRecording : startRecording}
          disabled={loading || transcribing}
          className={`p-2 rounded-md transition-all duration-200 ${
            recording
              ? 'bg-red-600 text-white animate-pulse shadow-[0_0_12px_rgba(239,68,68,0.5)]'
              : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white'
          } disabled:opacity-50`}
          title={recording ? 'Stop recording' : 'Voice input (Deepgram)'}
        >
          {recording ? <MicOff size={18} /> : <Mic size={18} />}
        </button>

        <input 
          type="text" 
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
          placeholder={recording ? '🔴 Listening...' : 'Ask for recommendations...'} 
          className="flex-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm text-slate-50 placeholder-slate-500"
          disabled={recording}
        />
        <button 
          onClick={() => sendMessage()}
          disabled={loading || !input.trim() || recording}
          className="bg-blue-600 text-white p-2 rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  );
}
