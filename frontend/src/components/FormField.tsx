import type { InputHTMLAttributes, ReactNode } from "react";

type FormFieldProps = InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string; hint?: ReactNode };

export function FormField({ label, error, hint, id, "aria-describedby": existingDescription, ...inputProps }: FormFieldProps) {
  const fieldId = id ?? inputProps.name;
  const helpId = error ? `${fieldId}-error` : hint ? `${fieldId}-hint` : undefined;
  const describedBy = [existingDescription, helpId].filter(Boolean).join(" ") || undefined;
  return <label htmlFor={fieldId} className="block text-base font-medium text-slate-800">
    {label}<input id={fieldId} {...inputProps} aria-describedby={describedBy} aria-invalid={error ? true : undefined} className={`mt-1.5 block min-h-11 w-full rounded-sm border px-3 py-2.5 font-normal text-slate-900 outline-none transition-colors focus:border-indigo-700 focus:ring-2 focus:ring-indigo-100 ${error ? "border-rose-500" : "border-slate-300"}`} />
    {error ? <span id={helpId} className="mt-1 block text-sm text-rose-800">{error}</span> : hint ? <span id={helpId} className="mt-1 block text-sm font-normal text-slate-600">{hint}</span> : null}
  </label>;
}
