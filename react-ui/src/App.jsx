import React, { useState, useRef, useEffect } from 'react';
import { Aperture, Chats, Bell, FolderOpen, Gear, MagnifyingGlass, FilmScript, Phone, VideoCamera, Files, SidebarSimple, Paperclip, Microphone, Smiley, PaperPlaneRight, CurrencyDollar, Lightning, CaretDown } from '@phosphor-icons/react';

function App() {
  const [messages, setMessages] = useState([
    {
      role: 'user',
      content: "Can you run a script doctor analysis on the pacing of the second act using the Hero's Journey framework? Also, I need real-time rental costs for an ARRI Alexa camera package for 3 days.",
      time: '10:42 AM'
    },
    {
      role: 'assistant',
      content: "Based on the **Hero's Journey** framework, the second act (The Road of Trials) in your script currently lacks a significant \"Belly of the Whale\" moment. The protagonist moves too smoothly from scene 24 to 36 without a major setback. I recommend introducing a minor conflict around page 40 to heighten the dramatic tension before the midpoint.",
      time: '10:45 AM',
      budgetData: "According to current real-world rental house listings (via parallel search), an **ARRI Alexa Mini LF package** averages between $1,200 - $1,500 per day. For a 3-day shoot, expect to budget roughly $3,600 - $4,500, not including specialized lenses or insurance.",
      toolLogs: ["parallel_search: rental costs ARRI Alexa", "script_doctor: hero's journey pacing act 2"]
    }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSend = async () => {
    if (!input.trim()) return;
    
    const newMsg = { role: 'user', content: input, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) };
    setMessages(prev => [...prev, newMsg]);
    setInput('');
    setIsTyping(true);

    try {
      // Assuming backend runs at localhost:8000
      const response = await fetch('/chat', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': 'Bearer demo_token'
        },
        body: JSON.stringify({
          session_id: "demo_react",
          query: input,
          system_instruction: "You are a filmmaking expert."
        })
      });
      
      const data = await response.json();
      
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response || "No response.",
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        toolLogs: data.tool_log || []
      }]);
    } catch (error) {
      console.error(error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: Could not connect to API. Is FastAPI running?`,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="h-screen w-full flex bg-obsidian text-gray-200 antialiased overflow-hidden selection:bg-nebula-violet selection:text-white">
      
      {/* 1. Navigation Hub (Left Strip) */}
      <nav className="w-16 h-full border-r border-white/5 flex flex-col items-center py-6 justify-between z-20 glass-panel shrink-0">
        <div className="flex flex-col gap-8 items-center w-full">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-glow cursor-pointer transition-transform duration-300 hover:scale-105">
            <Aperture weight="bold" className="text-xl text-white" />
          </div>
          
          <div className="flex flex-col gap-6 w-full items-center">
            <button className="relative text-white transition-colors duration-300">
              <Chats className="text-2xl" />
              <div className="absolute -left-4 top-1/2 -translate-y-1/2 w-1 h-5 bg-white rounded-r-full shadow-[0_0_8px_rgba(255,255,255,0.8)]"></div>
            </button>
            <button className="text-gray-500 hover:text-white transition-colors duration-300 relative">
              <Bell className="text-2xl" />
              <div className="absolute top-0 right-0 w-2 h-2 bg-nebula-violet rounded-full"></div>
            </button>
            <button className="text-gray-500 hover:text-white transition-colors duration-300">
              <FolderOpen className="text-2xl" />
            </button>
          </div>
        </div>

        <div className="flex flex-col gap-6 items-center">
          <button className="text-gray-500 hover:text-white transition-colors duration-300">
            <Gear className="text-2xl" />
          </button>
          <div className="relative cursor-pointer">
            <img src="https://ui-avatars.com/api/?name=DS&background=0D8ABC&color=fff" alt="User" className="w-10 h-10 rounded-full border border-white/10 transition-transform duration-300 hover:scale-105" />
            <div className="absolute bottom-0 right-0 w-3 h-3 bg-green-400 rounded-full border-2 border-slate shadow-[0_0_8px_rgba(74,222,128,0.5)]"></div>
          </div>
        </div>
      </nav>

      {/* 2. Conversation Directory (Left-Center Panel) */}
      <aside className="w-80 h-full border-r border-white/5 flex flex-col z-10 glass-panel bg-slate/40 shrink-0">
        <div className="p-6 pb-2">
          <h1 className="text-xl font-semibold tracking-tight text-white mb-4">Workspace</h1>
          
          <div className="relative group">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <MagnifyingGlass className="text-gray-500 group-focus-within:text-white transition-colors" />
            </div>
            <input type="text" className="w-full bg-white/5 border border-white/5 rounded-lg py-2 pl-10 pr-4 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-white/20 focus:bg-white/10 transition-all duration-300" placeholder="Search or jump..." />
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
              <span className="text-xs text-gray-500 font-mono">⌘K</span>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-2 mt-2">
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3 ml-2">Active</div>
          
          <div className="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/5 cursor-pointer transition-all duration-300 mb-1 relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-r from-nebula-violet/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <div className="relative">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-lg shadow-sm">🤖</div>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex justify-between items-baseline mb-0.5">
                <span className="text-sm font-medium text-white truncate">SceneIQ Agent</span>
                <span className="text-xs text-nebula-violet font-medium">Just now</span>
              </div>
              <p className="text-xs text-gray-400 truncate">I've completed the analysis.</p>
            </div>
            <div className="w-2 h-2 rounded-full bg-nebula-violet shadow-[0_0_8px_rgba(107,33,168,0.8)]"></div>
          </div>

          <div className="flex items-center gap-3 p-3 rounded-xl hover:bg-white/5 border border-transparent cursor-pointer transition-all duration-300 mb-1">
            <img src="https://ui-avatars.com/api/?name=Director&background=1E293B&color=fff" className="w-10 h-10 rounded-full opacity-80" alt="Avatar" />
            <div className="flex-1 min-w-0">
              <div className="flex justify-between items-baseline mb-0.5">
                <span className="text-sm font-medium text-gray-300 truncate">Director's Team</span>
                <span className="text-xs text-gray-600">2h</span>
              </div>
              <p className="text-xs text-gray-500 truncate">Can we review the pacing?</p>
            </div>
          </div>

          <div className="flex items-center gap-3 p-3 rounded-xl hover:bg-white/5 border border-transparent cursor-pointer transition-all duration-300 mb-1">
            <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center text-gray-400">
              <FilmScript className="text-xl" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex justify-between items-baseline mb-0.5">
                <span className="text-sm font-medium text-gray-300 truncate">Script Revisions</span>
                <span className="text-xs text-gray-600">Yesterday</span>
              </div>
              <p className="text-xs text-gray-500 truncate">Draft v4 uploaded.</p>
            </div>
          </div>
        </div>
      </aside>

      {/* 3. Primary Chat Canvas (Main Panel) */}
      <main className="flex-1 flex flex-col h-full relative min-w-0">
        <div className="absolute top-0 inset-x-0 h-96 bg-gradient-to-b from-nebula-violet/5 to-transparent pointer-events-none"></div>

        <header className="h-20 border-b border-white/5 flex items-center justify-between px-8 z-10 glass-panel shrink-0">
          <div className="flex items-center gap-4">
            <div className="flex flex-col">
              <h2 className="text-lg font-semibold tracking-tight text-white flex items-center gap-2">
                SceneIQ Agent
                <span className="px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-[10px] text-gray-400 tracking-wider font-mono">AI ASSISTANT</span>
              </h2>
              <span className="text-xs text-gray-500">Currently analyzing 'The Grand Nebula' Script</span>
            </div>
          </div>
          <div className="flex items-center gap-5 text-gray-400">
            <button className="hover:text-white hover:bg-white/5 p-2 rounded-lg transition-all"><Phone className="text-xl" /></button>
            <button className="hover:text-white hover:bg-white/5 p-2 rounded-lg transition-all"><VideoCamera className="text-xl" /></button>
            <div className="w-px h-6 bg-white/10 mx-1"></div>
            <button className="hover:text-white hover:bg-white/5 p-2 rounded-lg transition-all"><Files className="text-xl" /></button>
            <button className="hover:text-white hover:bg-white/5 p-2 rounded-lg transition-all"><SidebarSimple className="text-xl" /></button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto px-8 lg:px-24 py-8 z-10 space-y-8 pb-32">
          
          <div className="flex items-center justify-center msg-animate">
            <div className="h-px bg-white/5 flex-1"></div>
            <span className="mx-4 text-xs font-mono text-gray-600 tracking-widest">TODAY</span>
            <div className="h-px bg-white/5 flex-1"></div>
          </div>

          {messages.map((msg, idx) => (
            <div key={idx} className={`flex flex-col msg-animate ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
              <div className="flex items-baseline gap-2 mb-2">
                {msg.role === 'assistant' && (
                  <div className="w-6 h-6 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-xs shadow-glow">🤖</div>
                )}
                {msg.role === 'user' && <span className="text-[11px] text-gray-500 font-mono">{msg.time}</span>}
                <span className="text-sm font-medium text-gray-300">
                  {msg.role === 'user' ? 'You' : <span className="text-white">SceneIQ Agent</span>}
                </span>
                {msg.role === 'assistant' && <span className="text-[11px] text-gray-500 font-mono">{msg.time}</span>}
              </div>
              
              {msg.role === 'user' ? (
                <div className="max-w-2xl px-6 py-4 bg-white/5 border border-white/10 rounded-2xl rounded-tr-sm shadow-xl backdrop-blur-sm">
                  <p className="text-[15px] leading-relaxed font-light text-gray-200">{msg.content}</p>
                </div>
              ) : (
                <div className="max-w-3xl pr-12">
                  {msg.toolLogs && msg.toolLogs.length > 0 && (
                    <div className="flex items-center gap-2 mb-4 px-3 py-1.5 rounded-lg bg-white/5 border border-white/5 inline-flex backdrop-blur-sm group cursor-pointer hover:bg-white/10 transition-colors">
                      <Lightning weight="bold" className="text-nebula-violet animate-pulse" />
                      <span className="text-xs font-mono text-gray-400">Agent used {msg.toolLogs.length} tools</span>
                      <CaretDown className="text-gray-600 group-hover:text-gray-400 transition-colors" />
                    </div>
                  )}
                  <div className="prose prose-invert prose-p:text-[15px] prose-p:leading-relaxed prose-p:font-light prose-p:text-gray-300 max-w-none space-y-5">
                    <p>{msg.content}</p>
                    
                    {msg.budgetData && (
                      <div className="my-6 p-5 rounded-xl border border-white/10 bg-[#0A0D14] shadow-inner relative overflow-hidden group">
                        <div className="absolute left-0 top-0 bottom-0 w-1 bg-nebula-emerald shadow-[0_0_10px_#059669]"></div>
                        <h4 className="text-sm font-medium text-white flex items-center gap-2 mb-2">
                          <CurrencyDollar className="text-nebula-emerald" /> Real-time Budget Data
                        </h4>
                        <p className="text-sm text-gray-400 leading-relaxed">{msg.budgetData}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}

          {isTyping && (
            <div className="flex flex-col items-start msg-animate">
              <div className="flex items-center gap-2 px-5 py-3 rounded-2xl rounded-tl-sm bg-transparent border border-white/5">
                <div className="w-1.5 h-1.5 bg-gray-400 rounded-full dot-1"></div>
                <div className="w-1.5 h-1.5 bg-gray-400 rounded-full dot-2"></div>
                <div className="w-1.5 h-1.5 bg-gray-400 rounded-full dot-3"></div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Floating Input Deck */}
        <div className="absolute bottom-8 inset-x-0 flex justify-center px-8 z-30">
          <div className="w-full max-w-3xl glass-panel border border-white/10 rounded-full shadow-floating flex items-center px-2 py-2 transition-all duration-300 focus-within:border-white/30 focus-within:shadow-[0_20px_50px_-12px_rgba(107,33,168,0.2)]">
            <button className="p-3 text-gray-400 hover:text-white transition-colors rounded-full hover:bg-white/5">
              <Paperclip className="text-xl" />
            </button>
            <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              className="flex-1 bg-transparent border-none px-4 py-3 text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-0 text-[15px] font-light" 
              placeholder="Type a message..." 
            />
            <button className="p-3 text-gray-400 hover:text-white transition-colors rounded-full hover:bg-white/5">
              <Microphone className="text-xl" />
            </button>
            <button className="p-3 text-gray-400 hover:text-white transition-colors rounded-full hover:bg-white/5">
              <Smiley className="text-xl" />
            </button>
            <div className="ml-2 mr-1">
              <button onClick={handleSend} className="w-10 h-10 rounded-full bg-white text-obsidian flex items-center justify-center transition-transform hover:scale-105 active:scale-95 shadow-[0_0_15px_rgba(255,255,255,0.4)]">
                <PaperPlaneRight weight="fill" className="text-lg" />
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
