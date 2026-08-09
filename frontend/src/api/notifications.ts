import apiClient from './client';
import type { PaginatedResponse, ApiResponse } from '../types';
import type { Notification } from '../types/notification';

export interface NotificationResponse extends PaginatedResponse<Notification> {
  unread_count?: number;
}

export const notificationsApi = {
  getNotifications: (params?: { page?: number; unread?: boolean }) =>
    apiClient.get<NotificationResponse>('/notifications/', { params }),

  markAsRead: (id: string) =>
    apiClient.patch<ApiResponse<Notification>>(`/notifications/${id}/read/`),

  markAllAsRead: () =>
    apiClient.post<ApiResponse>('/notifications/mark-all-read/'),
};
