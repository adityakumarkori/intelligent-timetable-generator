import api from '@/services/api';
import { createResource, deleteResource, getResource, listResource, updateResource } from '@/services/crud';
import type {
  AcademicSession,
  Department,
  Division,
  Faculty,
  Page,
  Period,
  Room,
  Subject,
} from '@/types/api';
import type { ListParams } from '@/services/crud';

export const academicSessionApi = {
  list: (p?: ListParams) => listResource<AcademicSession>('/api/v1/academic-sessions', p),
  get: (id: string) => getResource<AcademicSession>('/api/v1/academic-sessions', id),
  create: (b: Record<string, unknown>) => createResource<AcademicSession>('/api/v1/academic-sessions', b),
  update: (id: string, b: Record<string, unknown>) =>
    updateResource<AcademicSession>('/api/v1/academic-sessions', id, b),
  remove: (id: string) => deleteResource('/api/v1/academic-sessions', id),
};

export const departmentApi = {
  list: (p?: ListParams) => listResource<Department>('/api/v1/departments', p),
  get: (id: string) => getResource<Department>('/api/v1/departments', id),
  create: (b: Record<string, unknown>) => createResource<Department>('/api/v1/departments', b),
  update: (id: string, b: Record<string, unknown>) =>
    updateResource<Department>('/api/v1/departments', id, b),
  remove: (id: string) => deleteResource('/api/v1/departments', id),
};

export const divisionApi = {
  list: (p?: ListParams) => listResource<Division>('/api/v1/divisions', p),
  get: (id: string) => getResource<Division>('/api/v1/divisions', id),
  create: (b: Record<string, unknown>) => createResource<Division>('/api/v1/divisions', b),
  update: (id: string, b: Record<string, unknown>) =>
    updateResource<Division>('/api/v1/divisions', id, b),
  remove: (id: string) => deleteResource('/api/v1/divisions', id),
};

export const subjectApi = {
  list: (p?: ListParams) => listResource<Subject>('/api/v1/subjects', p),
  get: (id: string) => getResource<Subject>('/api/v1/subjects', id),
  create: (b: Record<string, unknown>) => createResource<Subject>('/api/v1/subjects', b),
  update: (id: string, b: Record<string, unknown>) =>
    updateResource<Subject>('/api/v1/subjects', id, b),
  remove: (id: string) => deleteResource('/api/v1/subjects', id),
};

export const facultyApi = {
  list: (p?: ListParams) => listResource<Faculty>('/api/v1/faculty', p),
  get: (id: string) => getResource<Faculty>('/api/v1/faculty', id),
  create: (b: Record<string, unknown>) => createResource<Faculty>('/api/v1/faculty', b),
  update: (id: string, b: Record<string, unknown>) =>
    updateResource<Faculty>('/api/v1/faculty', id, b),
  remove: (id: string) => deleteResource('/api/v1/faculty', id),
};

export const roomApi = {
  list: (p?: ListParams) => listResource<Room>('/api/v1/rooms', p),
  get: (id: string) => getResource<Room>('/api/v1/rooms', id),
  create: (b: Record<string, unknown>) => createResource<Room>('/api/v1/rooms', b),
  update: (id: string, b: Record<string, unknown>) =>
    updateResource<Room>('/api/v1/rooms', id, b),
  remove: (id: string) => deleteResource('/api/v1/rooms', id),
};

export const periodApi = {
  list: (p?: ListParams) => listResource<Period>('/api/v1/periods', p),
  get: (id: string) => getResource<Period>('/api/v1/periods', id),
  create: (b: Record<string, unknown>) => createResource<Period>('/api/v1/periods', b),
  update: (id: string, b: Record<string, unknown>) =>
    updateResource<Period>('/api/v1/periods', id, b),
  remove: (id: string) => deleteResource('/api/v1/periods', id),
};

export type { Page };
export { api };
