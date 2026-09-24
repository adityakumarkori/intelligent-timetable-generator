import { describe, expect, it } from 'vitest';
import { parseApiError, periodLabel } from '@/services/api';

describe('parseApiError', () => {
  it('reads plain string details', () => {
    expect(parseApiError({ response: { status: 404, data: { detail: 'Gone' } } }).message).toBe('Gone');
  });

  it('extracts structured 409 conflicts and suggestions', () => {
    const info = parseApiError({
      response: {
        status: 409,
        data: {
          detail: {
            error: 'TIMETABLE_CONFLICT',
            conflicts: [
              {
                type: 'ROOM_CONFLICT',
                severity: 'ERROR',
                message: 'Room busy',
                subject: null,
                division: null,
                details: {},
                suggestions: ['Pick another room'],
              },
            ],
            suggestions: ['Pick another room'],
          },
        },
      },
    });
    expect(info.code).toBe('TIMETABLE_CONFLICT');
    expect(info.conflicts).toHaveLength(1);
    expect(info.message).toBe('Room busy');
    expect(info.suggestions).toEqual(['Pick another room']);
  });

  it('translates STALE_TIMETABLE into a refresh message', () => {
    const info = parseApiError({
      response: { status: 409, data: { detail: { error: 'STALE_TIMETABLE' } } },
    });
    expect(info.code).toBe('STALE_TIMETABLE');
    expect(info.message).toMatch(/changed by another action/i);
  });

  it('summarizes pydantic 422 arrays', () => {
    const info = parseApiError({
      response: {
        status: 422,
        data: { detail: [{ loc: ['body', 'capacity'], msg: 'Input should be greater than 0', type: 'x' }] },
      },
    });
    expect(info.message).toMatch(/capacity/);
  });

  it('maps 401/403/404/500 to friendly text', () => {
    expect(parseApiError({ response: { status: 401, data: {} } }).message).toMatch(/log in again/i);
    expect(parseApiError({ response: { status: 403, data: {} } }).message).toMatch(/permission/i);
    expect(parseApiError({ response: { status: 404, data: {} } }).message).toMatch(/not found/i);
    expect(parseApiError({ response: { status: 500, data: {} } }).message).toMatch(/server error/i);
  });
});

describe('periodLabel', () => {
  it('formats day, times, and order', () => {
    expect(
      periodLabel({ day_of_week: 'MONDAY', start_time: '09:00:00', end_time: '10:00:00', period_order: 1 }),
    ).toBe('Monday · 09:00–10:00 · P1');
  });
});
