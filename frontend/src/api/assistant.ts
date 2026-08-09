import apiClient from './client';
import type { PaginatedResponse } from '../types';
import { AIConversation, ChatRequest, ChatResponse } from '../types/assistant';

export const assistantApi = {
    getConversations: async (): Promise<AIConversation[]> => {
        const response = await apiClient.get<PaginatedResponse<AIConversation>>('/ai/conversations/');
        // The backend uses StandardPagination which wraps the array inside response.data.data
        return response.data.data || [];
    },
    
    getConversation: async (id: string): Promise<AIConversation> => {
        const response = await apiClient.get<AIConversation>(`/ai/conversations/${id}/`);
        return response.data;
    },

    sendMessage: async (data: ChatRequest): Promise<ChatResponse> => {
        const response = await apiClient.post<ChatResponse>('/ai/chat/', data);
        return response.data;
    }
};
