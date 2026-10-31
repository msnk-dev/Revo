import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { useState, type FormEvent, type ReactNode } from "react";
import { FormField } from "../../components/FormField";
import { useAuth } from "../../app/AuthContext";
import { apiRequest } from "../../api/client";

function AuthShell({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return <main className="grid min-h-screen place-items-center bg-slate-50 p-5"><section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm"><Link to="/login" className="text-xl font-bold text-indigo-700">revo<span className="text-slate-400">.</span></Link><h1 className="mt-8 text-2xl font-semibold">{title}</h1><p className="mt-2 text-sm text-slate-500">{description}</p>{children}</section></main>;
}

function ErrorNotice({ children }: { children: string }) { return <p role="alert" className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{children}</p>; }

function LoginPage() {
  const { user, signIn, loading } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  if (user) return <Navigate to="/" replace />;
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setSubmitting(true);
    const form = new FormData(event.currentTarget);
    try { await signIn(String(form.get("email")), String(form.get("password"))); navigate("/"); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Sign-in failed"); }
    finally { setSubmitting(false); }
  }
  return <AuthShell title="Welcome back" description="Sign in to manage your subscriptions.">
    {import.meta.env.VITE_USE_MOCKS === "true" && <p className="mt-4 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">Demo mode is on. Use any non-empty password; an email containing “customer” opens the customer portal.</p>}
    <form className="mt-6 space-y-4" onSubmit={submit}><FormField label="Email" name="email" type="email" autoComplete="email" required /><FormField label="Password" name="password" type="password" autoComplete="current-password" required />{error && <ErrorNotice>{error}</ErrorNotice>}<button disabled={submitting || loading} className="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{submitting ? "Signing in…" : "Sign in"}</button></form>
    <div className="mt-5 flex justify-between text-sm text-indigo-700"><Link to="/signup">Create account</Link><Link to="/forgot">Forgot password?</Link></div>
  </AuthShell>;
}

function SignupPage() {
  const navigate = useNavigate(); const [error, setError] = useState(""); const [done, setDone] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); const form = new FormData(event.currentTarget);
    try { await apiRequest("/auth/signup", { method: "POST", body: JSON.stringify({ name: form.get("name"), email: form.get("email"), password: form.get("password") }) }); setDone(true); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Signup failed"); }
  }
  return <AuthShell title="Create your account" description="Set up your customer portal access."><form className="mt-6 space-y-4" onSubmit={submit}><FormField label="Full name" name="name" autoComplete="name" required /><FormField label="Email" name="email" type="email" autoComplete="email" required /><FormField label="Password" name="password" type="password" autoComplete="new-password" minLength={9} pattern="(?=.*[a-z])(?=.*[A-Z])(?=.*[^A-Za-z0-9]).{9,}" hint="At least 9 characters with uppercase, lowercase, and a special character." required />{error && <ErrorNotice>{error}</ErrorNotice>}{done ? <div role="status" className="space-y-3 text-sm text-emerald-700">Account created. You can now sign in.<button type="button" onClick={() => navigate("/login")} className="block font-semibold underline">Continue to sign in</button></div> : <button className="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white">Create account</button>}</form><Link className="mt-5 inline-block text-sm text-indigo-700" to="/login">Back to sign in</Link></AuthShell>;
}

function ForgotPage() {
  const [done, setDone] = useState(false); const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); const form = new FormData(event.currentTarget);
    try { await apiRequest("/auth/forgot", { method: "POST", body: JSON.stringify({ email: form.get("email") }) }); setDone(true); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Request failed"); }
  }
  return <AuthShell title="Reset your password" description="We’ll send a reset link if the account exists.">{done ? <p role="status" className="mt-6 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">If the email is registered, reset instructions have been sent.</p> : <form className="mt-6 space-y-4" onSubmit={submit}><FormField label="Email" name="email" type="email" autoComplete="email" required />{error && <ErrorNotice>{error}</ErrorNotice>}<button className="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white">Send reset link</button></form>}<Link className="mt-5 inline-block text-sm text-indigo-700" to="/login">Back to sign in</Link></AuthShell>;
}

function ResetPage() {
  const [search] = useSearchParams(); const token = search.get("token") ?? ""; const [done, setDone] = useState(false); const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); const form = new FormData(event.currentTarget);
    try { await apiRequest("/auth/reset", { method: "POST", body: JSON.stringify({ token, new_password: form.get("password") }) }); setDone(true); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Password reset failed"); }
  }
  return <AuthShell title="Choose a new password" description="Set a new password for your Revo account.">{done ? <p role="status" className="mt-6 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">Password updated. <Link className="font-semibold underline" to="/login">Sign in</Link></p> : <form className="mt-6 space-y-4" onSubmit={submit}><FormField label="Reset token" name="token" value={token} readOnly hint="This value comes from your reset link." /><FormField label="New password" name="password" type="password" autoComplete="new-password" minLength={9} pattern="(?=.*[a-z])(?=.*[A-Z])(?=.*[^A-Za-z0-9]).{9,}" required />{error && <ErrorNotice>{error}</ErrorNotice>}<button disabled={!token} className="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">Update password</button></form>}</AuthShell>;
}

export const routes = [
  { path: "/login", element: <LoginPage /> },
  { path: "/signup", element: <SignupPage /> },
  { path: "/forgot", element: <ForgotPage /> },
  { path: "/reset", element: <ResetPage /> },
];
