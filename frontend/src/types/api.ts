/** Backend API types mirroring the OpenAPI schemas. No `any`, no TS enums
 *  (erasableSyntaxOnly): string unions + const option lists instead. */

export const USER_ROLES = ['SUPER_ADMIN', 'ADMIN', 'FACULTY', 'STUDENT'] as const;
export type UserRole = (typeof USER_ROLES)[number];

export const TIMETABLE_STATUSES = ['DRAFT', 'GENERATED', 'VALID', 'PUBLISHED', 'ARCHIVED'] as const;
export type TimetableStatus = (typeof TIMETABLE_STATUSES)[number];

export const DAYS_OF_WEEK = [
  'MONDAY',
  'TUESDAY',
  'WEDNESDAY',
  'THURSDAY',
  'FRIDAY',
  'SATURDAY',
  'SUNDAY',
] as const;
export type DayOfWeek = (typeof DAYS_OF_WEEK)[number];

export const ROOM_TYPES = ['CLASSROOM', 'LAB', 'SEMINAR_ROOM', 'OTHER'] as const;
export type RoomType = (typeof ROOM_TYPES)[number];

export const SUBJECT_TYPES = ['LECTURE', 'LAB', 'TUTORIAL', 'PRACTICAL', 'OTHER'] as const;
export type SubjectType = (typeof SUBJECT_TYPES)[number];

export const AVAILABILITY_STATUSES = ['AVAILABLE', 'UNAVAILABLE'] as const;
export type AvailabilityStatus = (typeof AVAILABILITY_STATUSES)[number];

export interface Page<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface AcademicSession {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Department {
  id: string;
  name: string;
  code: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Division {
  id: string;
  department_id: string;
  name: string;
  code: string;
  student_count: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Subject {
  id: string;
  code: string;
  name: string;
  subject_type: SubjectType;
  required_periods_per_week: number;
  required_room_type: RoomType | null;
  requires_lab: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Faculty {
  id: string;
  user_id: string | null;
  employee_code: string;
  department_id: string;
  name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Room {
  id: string;
  name: string;
  room_type: RoomType;
  capacity: number;
  building: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Period {
  id: string;
  day_of_week: DayOfWeek;
  start_time: string;
  end_time: string;
  period_order: number;
  is_break: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PeriodBrief {
  id: string;
  day_of_week: DayOfWeek;
  start_time: string;
  end_time: string;
  period_order: number;
  is_break: boolean;
}

export interface SubjectBrief {
  id: string;
  code: string;
  name: string;
}

export interface FacultyBrief {
  id: string;
  employee_code: string;
  name: string;
}

export interface RoomBrief {
  id: string;
  name: string;
  room_type: RoomType;
}

export interface Availability {
  id: string;
  faculty_id: string;
  period_id: string;
  status: AvailabilityStatus;
  period: PeriodBrief;
}

export interface FacultyAssignment {
  id: string;
  faculty_id: string;
  subject_id: string;
  division_id: string;
  academic_session_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  faculty_name: string;
  subject_code: string;
  division_code: string;
}

export interface DivisionSubjectRequirement {
  id: string;
  division_id: string;
  subject_id: string;
  academic_session_id: string;
  required_periods_per_week: number;
  preferred_room_type: RoomType | null;
  requires_lab: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  subject_code: string;
  division_code: string;
}

export interface Timetable {
  id: string;
  academic_session_id: string;
  session_name: string;
  division_id: string;
  division_code: string;
  status: TimetableStatus;
  version: number;
  generated_at: string | null;
  published_at: string | null;
  entry_count: number;
  created_at: string;
  updated_at: string;
}

export interface TimetableEntry {
  id: string;
  timetable_id: string;
  division_code: string;
  subject_id: string;
  subject_code: string;
  subject_name: string;
  faculty_id: string;
  faculty_name: string;
  room_id: string;
  room_name: string;
  period: PeriodBrief;
}

export interface TimetableDetail extends Timetable {
  entries: TimetableEntry[];
}

export interface TimetableEntryDetail {
  id: string;
  timetable_id: string;
  period: PeriodBrief;
  subject: SubjectBrief;
  faculty: FacultyBrief;
  room: RoomBrief;
}

export interface Conflict {
  type: string;
  severity: string;
  message: string;
  subject: string | null;
  division: string | null;
  details: Record<string, unknown>;
  suggestions: string[];
}

export interface Violation {
  type: string;
  message: string;
  details: Record<string, unknown>;
}

export interface GenerationSuccess {
  status: 'SUCCESS';
  timetable_id: string;
  solver_status: string;
  objective_score: number | null;
  generation_duration_ms: number;
  warnings: string[];
}

export interface GenerationFailure {
  status: string;
  solver_status: string;
  conflicts: Conflict[];
  suggestions: string[];
  generation_duration_ms: number;
}

export interface ValidateResult {
  timetable_id: string;
  valid: boolean;
  violations: Violation[];
  status: string;
  errors: Violation[];
  warnings: string[];
  score: number | null;
}

export interface GenerationResultView {
  timetable_id: string;
  status: TimetableStatus;
  version: number;
  generated_at: string | null;
  entry_count: number;
  valid: boolean;
  violations: Violation[];
}

export interface CloneResult {
  id: string;
  academic_session_id: string;
  division_id: string;
  status: TimetableStatus;
  version: number;
  entry_count: number;
  valid: boolean;
  violations: Violation[];
  warnings: string[];
}

export interface GenerationOptions {
  optimize: boolean;
  time_limit_seconds: number;
  num_workers?: number | null;
  random_seed?: number | null;
}
