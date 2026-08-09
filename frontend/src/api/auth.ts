import apiClient from './client';
import type { ApiResponse, AuthTokens, LoginCredentials, RegisterData, User } from '../types';

export const authApi = {
  register: (data: RegisterData) =>
    apiClient.post<ApiResponse<User>>('/auth/register/', data),

  login: (credentials: LoginCredentials) =>
    apiClient.post<ApiResponse<AuthTokens>>('/auth/login/', credentials),

  refresh: (refreshToken: string) =>
    apiClient.post<ApiResponse<{ access: string; refresh: string }>>('/auth/refresh/', {
      refresh: refreshToken,
    }),

  logout: (refreshToken: string) =>
    apiClient.post<ApiResponse>('/auth/logout/', { refresh: refreshToken }),

  getMe: () =>
    apiClient.get<ApiResponse<User>>('/auth/me/'),

  updateProfile: (data: Partial<Pick<User, 'first_name' | 'last_name' | 'phone_number'>>) =>
    apiClient.patch<ApiResponse<User>>('/auth/me/', data),

  changePassword: (data: { old_password: string; new_password: string; confirm_new_password: string }) =>
    apiClient.post<ApiResponse>('/auth/change-password/', data),
};
