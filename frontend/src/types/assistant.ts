export interface AIMessage {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    created_at: string;
}

export interface AIConversation {
    id: string;
    title: string;
    created_at: string;
    messages: AIMessage[];
}

export interface ChatRequest {
    message: string;
    conversation_id?: string;
}

export interface ChatResponse {
    conversation_id: string;
    title: string;
    message: string;
}
