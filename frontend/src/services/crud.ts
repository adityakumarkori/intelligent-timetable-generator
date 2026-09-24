import api from '@/services/api';
import type { Page } from '@/types/api';

export interface ListParams {
  page?: number;
  page_size?: number;
  q?: string;
  is_active?: boolean;
  [key: string]: string | number | boolean | undefined;
}

export async function listResource<T>(base: string, params: ListParams = {}): Promise<Page<T>> {
  const { data } = await api.get<Page<T>>(base, { params });
  return data;
}

export async function getResource<T>(base: string, id: string): Promise<T> {
  const { data } = await api.get<T>(`${base}/${id}`);
  return data;
}

export async function createResource<T>(base: string, payload: Record<string, unknown>): Promise<T> {
  const { data } = await api.post<T>(base, payload);
  return data;
}

export async function updateResource<T>(
  base: string,
  id: string,
  payload: Record<string, unknown>,
): Promise<T> {
  const { data } = await api.patch<T>(`${base}/${id}`, payload);
  return data;
}

export async function deleteResource(base: string, id: string): Promise<void> {
  await api.delete(`${base}/${id}`);
}
