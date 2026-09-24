import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useRef, useState } from 'react';

/** Minute granularity for the dropdowns. School periods land on these. */
export const TIME_MINUTE_STEP = 5;

const HOURS = Array.from({ length: 24 }, (_, h) => String(h).padStart(2, '0'));
const MINUTES = Array.from({ length: 60 / TIME_MINUTE_STEP }, (_, i) =>
  String(i * TIME_MINUTE_STEP).padStart(2, '0'),
);

function split(value?: string): { hour: string; minute: string } {
  const match = /^(\d{2}):(\d{2})/.exec(value ?? '');
  return { hour: match?.[1] ?? '', minute: match?.[2] ?? '' };
}

/** No-scroll time picker: hour + minute dropdowns emitting "HH:MM".
 *  Untouched values (e.g. "HH:MM:SS" from the API, or off-step minutes)
 *  pass through unchanged until the user picks a part. */
export function TimeSelect({
  value,
  onChange,
  disabled,
}: {
  value?: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  const parsed = split(value);
  const initialMinute = MINUTES.includes(parsed.minute) ? parsed.minute : '';
  // Pending parts live locally so hour-then-minute picking works even
  // though the parent only hears about complete "HH:MM" values.
  const [hour, setHour] = useState(parsed.hour);
  const [minute, setMinute] = useState(initialMinute);
  // Re-sync when the parent resets or loads a different value.
  const prevValue = useRef(value);
  if (prevValue.current !== value) {
    prevValue.current = value;
    const next = split(value);
    setHour(next.hour);
    setMinute(MINUTES.includes(next.minute) ? next.minute : '');
  }

  function pickHour(h: string) {
    setHour(h);
    if (minute) onChange(`${h}:${minute}`);
  }

  function pickMinute(m: string) {
    setMinute(m);
    if (hour) onChange(`${hour}:${m}`);
  }

  return (
    <div className="flex gap-2">
      <Select value={hour} onValueChange={pickHour} disabled={disabled}>
        <SelectTrigger aria-label="Hour">
          <SelectValue placeholder="HH" />
        </SelectTrigger>
        <SelectContent>
          {HOURS.map((h) => (
            <SelectItem key={h} value={h}>
              {h}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <span className="self-center font-semibold text-slate-400" aria-hidden>
        :
      </span>
      <Select value={minute} onValueChange={pickMinute} disabled={disabled}>
        <SelectTrigger aria-label="Minute">
          <SelectValue placeholder="MM" />
        </SelectTrigger>
        <SelectContent>
          {MINUTES.map((m) => (
            <SelectItem key={m} value={m}>
              {m}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
