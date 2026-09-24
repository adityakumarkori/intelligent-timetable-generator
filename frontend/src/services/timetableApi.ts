import api from '@/services/api';
import { AxiosError } from 'axios';
import type {
  CloneResult,
  GenerationFailure,
  GenerationOptions,
  GenerationResultView,
  GenerationSuccess,
  TimetableDetail,
  TimetableEntryDetail,
  ValidateResult,
} from '@/types/api';
import type { ListParams } from '@/services/crud';
import { listResource } from '@/services/crud';
import type { Timetable } from '@/types/api';

export const timetableApi = {
  list: (p?: ListParams) => listResource<Timetable>('/api/v1/timetables', p),
  get: (id: string) =>
    api.get<TimetableDetail>(`/api/v1/timetables/${id}`).then((r) => r.data),
  divisionTimetable: (divisionId: string) =>
    api.get<TimetableDetail>(`/api/v1/divisions/${divisionId}/timetable`).then((r) => r.data),
  facultyTimetable: (facultyId: string, p?: ListParams) =>
    api
      .get<{ items: TimetableDetail['entries']; page: number; page_size: number; total: number }>(
        `/api/v1/faculty/${facultyId}/timetable`,
        { params: p },
      )
      .then((r) => r.data),

  generate: async (
    academicSessionId: string,
    divisionId: string,
    options: GenerationOptions,
  ): Promise<GenerationSuccess | GenerationFailure> => {
    try {
      const { data } = await api.post<GenerationSuccess>('/api/v1/timetables/generate', {
        academic_session_id: academicSessionId,
        division_id: divisionId,
        options,
      });
      return data;
    } catch (error) {
      // Infeasible configuration → 422 with a structured conflict body (not an error).
      if (
        error instanceof AxiosError &&
        error.response?.status === 422 &&
        typeof error.response.data?.status === 'string'
      ) {
        return error.response.data as GenerationFailure;
      }
      throw error;
    }
  },

  validate: (id: string) =>
    api.post<ValidateResult>(`/api/v1/timetables/${id}/validate`).then((r) => r.data),

  generationResult: (id: string) =>
    api.get<GenerationResultView>(`/api/v1/timetables/${id}/generation-result`).then((r) => r.data),

  createEntry: (
    timetableId: string,
    body: { subject_id: string; faculty_id: string; room_id: string; period_id: string },
    ifUnmodifiedSince?: string | null,
  ) =>
    api
      .post<TimetableEntryDetail>(`/api/v1/timetables/${timetableId}/entries`, body, {
        headers: ifUnmodifiedSince ? { 'If-Unmodified-Since': ifUnmodifiedSince } : undefined,
      })
      .then((r) => r.data),

  updateEntry: (
    timetableId: string,
    entryId: string,
    body: { subject_id?: string; faculty_id?: string; room_id?: string; period_id?: string },
    ifUnmodifiedSince?: string | null,
  ) =>
    api
      .patch<TimetableEntryDetail>(
        `/api/v1/timetables/${timetableId}/entries/${entryId}`,
        body,
        {
          headers: ifUnmodifiedSince ? { 'If-Unmodified-Since': ifUnmodifiedSince } : undefined,
        },
      )
      .then((r) => r.data),

  deleteEntry: (timetableId: string, entryId: string) =>
    api.delete(`/api/v1/timetables/${timetableId}/entries/${entryId}`).then((r) => r.data),

  publish: (id: string, ifUnmodifiedSince?: string | null) =>
    api
      .post<TimetableDetail>(`/api/v1/timetables/${id}/publish`, null, {
        headers: ifUnmodifiedSince ? { 'If-Unmodified-Since': ifUnmodifiedSince } : undefined,
      })
      .then((r) => r.data),

  archive: (id: string) =>
    api.post<TimetableDetail>(`/api/v1/timetables/${id}/archive`).then((r) => r.data),

  clone: (id: string) =>
    api.post<CloneResult>(`/api/v1/timetables/${id}/clone`).then((r) => r.data),
};

export type { GenerationFailure };
