import api from '@/services/api';
import type { TokenResponse, User } from '@/types/api';

export async function login(email: string, password: string): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>('/api/v1/auth/login', { email, password });
  return data;
}

export async function fetchMe(): Promise<User> {
  const { data } = await api.get<User>('/api/v1/auth/me');
  return data;
}
