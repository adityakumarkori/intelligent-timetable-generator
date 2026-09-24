import api from '@/services/api';
import { createResource, deleteResource, getResource, listResource, updateResource } from '@/services/crud';
import type {
  Availability,
  AvailabilityStatus,
  DivisionSubjectRequirement,
  FacultyAssignment,
} from '@/types/api';
import type { ListParams } from '@/services/crud';

export const availabilityApi = {
  list: (facultyId: string) =>
    api.get<Availability[]>(`/api/v1/faculty/${facultyId}/availability`).then((r) => r.data),
  replace: (facultyId: string, items: { period_id: string; status: AvailabilityStatus }[]) =>
    api
      .put<Availability[]>(`/api/v1/faculty/${facultyId}/availability`, { items })
      .then((r) => r.data),
  setOne: (facultyId: string, periodId: string, statusValue: AvailabilityStatus) =>
    api
      .patch<Availability>(`/api/v1/faculty/${facultyId}/availability/${periodId}`, {
        status: statusValue,
      })
      .then((r) => r.data),
};

export const assignmentApi = {
  list: (p?: ListParams) => listResource<FacultyAssignment>('/api/v1/faculty-assignments', p),
  get: (id: string) => getResource<FacultyAssignment>('/api/v1/faculty-assignments', id),
  create: (b: Record<string, unknown>) =>
    createResource<FacultyAssignment>('/api/v1/faculty-assignments', b),
  remove: (id: string) => deleteResource('/api/v1/faculty-assignments', id),
};

export const requirementApi = {
  list: (p?: ListParams) =>
    listResource<DivisionSubjectRequirement>('/api/v1/division-subject-requirements', p),
  get: (id: string) =>
    getResource<DivisionSubjectRequirement>('/api/v1/division-subject-requirements', id),
  create: (b: Record<string, unknown>) =>
    createResource<DivisionSubjectRequirement>('/api/v1/division-subject-requirements', b),
  update: (id: string, b: Record<string, unknown>) =>
    updateResource<DivisionSubjectRequirement>('/api/v1/division-subject-requirements', id, b),
  remove: (id: string) => deleteResource('/api/v1/division-subject-requirements', id),
};
