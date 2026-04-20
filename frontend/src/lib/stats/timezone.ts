const dayInMs = 24 * 60 * 60 * 1000;
const zonedDatePartFormatters = new Map<string, Intl.DateTimeFormat>();

type ZonedDateParts = {
  year: number;
  month: number;
  day: number;
  hour: number;
  minute: number;
};

function zonedDatePartFormatter(timeZone: string): Intl.DateTimeFormat {
  const cached = zonedDatePartFormatters.get(timeZone);
  if (cached) {
    return cached;
  }

  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23'
  });
  zonedDatePartFormatters.set(timeZone, formatter);
  return formatter;
}

function zonedDateParts(value: Date, timeZone: string): ZonedDateParts {
  const parts = zonedDatePartFormatter(timeZone).formatToParts(value);
  const values = Object.fromEntries(parts.filter((part) => part.type !== 'literal').map((part) => [part.type, part.value]));
  return {
    year: Number(values.year),
    month: Number(values.month),
    day: Number(values.day),
    hour: Number(values.hour),
    minute: Number(values.minute)
  };
}

function dayNumberDate(dayNumber: number): Date {
  return new Date(dayNumber * dayInMs);
}

export function zonedDayNumber(value: Date, timeZone: string): number {
  const parts = zonedDateParts(value, timeZone);
  return Math.floor(Date.UTC(parts.year, parts.month - 1, parts.day) / dayInMs);
}

export function formatCalendarDay(dayNumber: number, options: Intl.DateTimeFormatOptions): string {
  return dayNumberDate(dayNumber).toLocaleDateString(undefined, { ...options, timeZone: 'UTC' });
}

export function parseRetryDueAt(value: string | null | undefined): Date | null {
  if (!value) {
    return null;
  }
  const dueAt = new Date(value);
  return Number.isNaN(dueAt.getTime()) ? null : dueAt;
}

export function startOfLocalHour(value: Date): Date {
  const date = new Date(value);
  date.setMinutes(0, 0, 0);
  return date;
}

export const timeConstants = {
  dayInMs,
  hourInMs: 60 * 60 * 1000
};
