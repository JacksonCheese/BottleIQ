export type Tone = "good" | "bad" | "neutral";

// lowerIsBetter is null for numbers where neither direction is clearly better.
export function change(
  before: number,
  now: number,
  lowerIsBetter: boolean | null,
): { delta: number; percent: number | null; tone: Tone } {
  const delta = now - before;
  const tone: Tone =
    delta === 0 || lowerIsBetter === null
      ? "neutral"
      : delta < 0 === lowerIsBetter
        ? "good"
        : "bad";
  return {
    delta,
    percent: before === 0 ? null : delta / Math.abs(before),
    tone,
  };
}

export const percent = (value: number) =>
  `${value > 0 ? "+" : ""}${Math.round(value * 100)}%`;

// API dates are store-local calendar days; parse them without a timezone shift.
const day = (iso: string) => {
  const [year, month, date] = iso.split("-").map(Number);
  return new Date(year, month - 1, date);
};

export const shortDate = (iso: string) =>
  day(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

export function periodLabel(start: string, end: string) {
  const sameYear = start.slice(0, 4) === end.slice(0, 4);
  const first = day(start).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    ...(sameYear ? {} : { year: "numeric" }),
  });
  return `${first} – ${shortDate(end)}`;
}

export const monthLabel = (month: string) =>
  day(`${month}-01`).toLocaleDateString("en-US", {
    month: "short",
    year: "numeric",
  });
