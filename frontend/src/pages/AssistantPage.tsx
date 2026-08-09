import React, { useState, useEffect, useRef } from 'react';
import { assistantApi } from '../api/assistant';
import { AIConversation, AIMessage } from '../types/assistant';
import { Send, Bot, User, PlusCircle } from 'lucide-react';

const AssistantPage: React.FC = () => {
    const [conversations, setConversations] = useState<AIConversation[]>([]);
    const [activeConv, setActiveConv] = useState<AIConversation | null>(null);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        loadConversations();
    }, []);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [activeConv?.messages]);

    const loadConversations = async () => {
        try {
            const data = await assistantApi.getConversations();
            setConversations(data);
            if (data.length > 0 && !activeConv) {
                loadConversation(data[0].id);
            }
        } catch (error) {
            console.error("Failed to load conversations", error);
        }
    };

    const loadConversation = async (id: string) => {
        try {
            const data = await assistantApi.getConversation(id);
            setActiveConv(data);
        } catch (error) {
            console.error("Failed to load conversation", error);
        }
    };

    const handleNewChat = () => {
        setActiveConv(null);
    };

    const handleSend = async () => {
        if (!input.trim()) return;
        
        const userMsg: AIMessage = {
            id: Date.now().toString(),
            role: 'user',
            content: input,
            created_at: new Date().toISOString()
        };

        const currentConv = activeConv ? { ...activeConv } : {
            id: '',
            title: 'New Conversation',
            created_at: new Date().toISOString(),
            messages: []
        };

        currentConv.messages = [...(currentConv.messages || []), userMsg];
        setActiveConv(currentConv as AIConversation);
        setInput('');
        setLoading(true);

        try {
            const res = await assistantApi.sendMessage({
                message: userMsg.content,
                conversation_id: activeConv ? activeConv.id : undefined
            });

            if (!activeConv) {
                // Was a new conversation, fetch updated list
                await loadConversations();
                await loadConversation(res.conversation_id);
            } else {
                await loadConversation(activeConv.id);
            }
        } catch (error) {
            console.error("Failed to send message", error);
            const errMsgs = [...currentConv.messages, {
                id: Date.now().toString(),
                role: 'assistant',
                content: 'Sorry, I encountered an error. Please try again.',
                created_at: new Date().toISOString()
            }];
            setActiveConv({ ...currentConv, messages: errMsgs } as AIConversation);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex h-[calc(100vh-6rem)] overflow-hidden bg-gray-50 rounded-lg shadow-sm border border-gray-100">
            {/* Sidebar for History */}
            <div className="w-1/4 bg-white border-r border-gray-100 flex flex-col">
                <div className="p-4 border-b border-gray-100">
                    <button 
                        onClick={handleNewChat}
                        className="w-full flex items-center justify-center space-x-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition"
                    >
                        <PlusCircle size={18} />
                        <span>New Chat</span>
                    </button>
                </div>
                <div className="flex-1 overflow-y-auto p-2 space-y-1">
                    {conversations.map(conv => (
                        <button
                            key={conv.id}
                            onClick={() => loadConversation(conv.id)}
                            className={`w-full text-left p-3 rounded-lg text-sm truncate transition ${
                                activeConv?.id === conv.id ? 'bg-indigo-50 text-indigo-700 font-medium' : 'hover:bg-gray-50 text-gray-700'
                            }`}
                        >
                            {conv.title}
                        </button>
                    ))}
                </div>
            </div>

            {/* Chat Area */}
            <div className="flex-1 flex flex-col bg-white">
                <div className="flex-1 overflow-y-auto p-6 space-y-6">
                    {!activeConv?.messages?.length ? (
                        <div className="h-full flex flex-col items-center justify-center text-gray-400 space-y-4">
                            <Bot size={48} className="text-indigo-200" />
                            <h2 className="text-xl font-medium text-gray-600">PayPlatform AI Assistant</h2>
                            <p className="text-sm text-center max-w-md">
                                Ask me about your wallet balance, recent transactions, or spending summaries.
                            </p>
                            <div className="flex flex-wrap justify-center gap-2 mt-4">
                                {["What is my wallet balance?", "Show my recent transactions", "How much did I deposit this month?"].map(q => (
                                    <button 
                                        key={q}
                                        onClick={() => setInput(q)}
                                        className="text-xs bg-gray-100 text-gray-600 px-3 py-1.5 rounded-full hover:bg-indigo-50 hover:text-indigo-600 transition"
                                    >
                                        {q}
                                    </button>
                                ))}
                            </div>
                        </div>
                    ) : (
                        activeConv.messages.map((msg, i) => (
                            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                <div className={`flex items-start max-w-[80%] space-x-3 ${msg.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`}>
                                    <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                                        msg.role === 'user' ? 'bg-indigo-100 text-indigo-600' : 'bg-green-100 text-green-600'
                                    }`}>
                                        {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                                    </div>
                                    <div className={`p-4 rounded-2xl ${
                                        msg.role === 'user' ? 'bg-indigo-600 text-white rounded-tr-sm' : 'bg-gray-100 text-gray-800 rounded-tl-sm'
                                    }`}>
                                        <p className="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</p>
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                    {loading && (
                        <div className="flex justify-start">
                            <div className="flex items-center space-x-2 bg-gray-50 text-gray-500 p-3 rounded-2xl rounded-tl-sm">
                                <Bot size={16} className="animate-pulse" />
                                <span className="text-sm font-medium animate-pulse">Thinking...</span>
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                <div className="p-4 border-t border-gray-100">
                    <form 
                        onSubmit={(e) => { e.preventDefault(); handleSend(); }}
                        className="flex items-center space-x-2 bg-gray-50 p-2 rounded-xl border border-gray-200 focus-within:border-indigo-500 focus-within:ring-1 focus-within:ring-indigo-500 transition"
                    >
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder="Ask about your finances..."
                            className="flex-1 bg-transparent border-none focus:outline-none focus:ring-0 text-sm px-2"
                            disabled={loading}
                        />
                        <button
                            type="submit"
                            disabled={!input.trim() || loading}
                            className="bg-indigo-600 text-white p-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
                        >
                            <Send size={18} />
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
};

export default AssistantPage;
