import type { InputHTMLAttributes, ReactNode } from "react";

type FormFieldProps = InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string; hint?: ReactNode };

export function FormField({ label, error, hint, id, ...inputProps }: FormFieldProps) {
  const fieldId = id ?? inputProps.name;
  return <label htmlFor={fieldId} className="block text-sm font-medium text-slate-700">
    {label}<input id={fieldId} {...inputProps} className={`mt-1.5 block w-full rounded-lg border px-3 py-2.5 font-normal outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 ${error ? "border-rose-400" : "border-slate-300"}`} />
    {error ? <span className="mt-1 block text-xs text-rose-600">{error}</span> : hint ? <span className="mt-1 block text-xs font-normal text-slate-500">{hint}</span> : null}
  </label>;
}
