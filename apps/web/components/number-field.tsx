"use client";

type NumberFieldProps = {
  id: string;
  label: string;
  value: number;
  onChange: (value: number) => void;
  placeholder?: string;
  size?: "md" | "lg";
};

const MAX = 1_000_000_000;

function parse(value: string): number {
  const digits = value.replace(/[^0-9]/g, "");
  if (!digits) return 0;
  return Math.min(Number(digits), MAX);
}

function display(value: number): string {
  return value === 0 ? "" : value.toLocaleString("ko-KR");
}

export function NumberField({ id, label, value, onChange, placeholder = "0", size = "md" }: NumberFieldProps) {
  return (
    <div className="relative">
      <label htmlFor={id} className="sr-only">
        {label}
      </label>
      <input
        id={id}
        type="text"
        inputMode="numeric"
        autoComplete="off"
        value={display(value)}
        placeholder={placeholder}
        onChange={(event) => onChange(parse(event.target.value))}
        className={[
          "w-full rounded-xl border border-zinc-200 bg-white pr-9 text-right font-medium tabular-nums text-zinc-900",
          "placeholder:text-zinc-300 focus:border-zinc-900 focus:outline-none focus:ring-2 focus:ring-zinc-900/10",
          size === "lg" ? "h-14 pl-4 text-xl" : "h-11 pl-3 text-base",
        ].join(" ")}
      />
      <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-sm text-zinc-400">원</span>
    </div>
  );
}
