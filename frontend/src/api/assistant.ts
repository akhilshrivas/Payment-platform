import apiClient from './client';
import { AIConversation, ChatRequest, ChatResponse } from '../types/assistant';

export const assistantApi = {
    getConversations: async (): Promise<AIConversation[]> => {
        const response = await apiClient.get('/ai/conversations/');
        return response.data.results || response.data;
    },
    
    getConversation: async (id: string): Promise<AIConversation> => {
        const response = await apiClient.get(`/ai/conversations/${id}/`);
        return response.data;
    },

    sendMessage: async (data: ChatRequest): Promise<ChatResponse> => {
        const response = await apiClient.post('/ai/chat/', data);
        return response.data;
    }
};
