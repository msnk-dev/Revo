import { Link, Navigate, useNavigate } from "react-router-dom";
import { FormField } from "../../components/FormField";
import { useAuth } from "../../app/AuthContext";

function LoginPage() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  if (user) return <Navigate to="/" replace />;
  return <main className="grid min-h-screen place-items-center bg-slate-50 p-5"><section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm"><p className="text-xl font-bold text-indigo-700">revo<span className="text-slate-400">.</span></p><h1 className="mt-8 text-2xl font-semibold">Welcome back</h1><p className="mt-2 text-sm text-slate-500">Sign in to manage your subscriptions.</p><form className="mt-6 space-y-4" onSubmit={(event) => { event.preventDefault(); setUser({ id: 1, name: "Demo User", role: "admin" }); navigate("/"); }}><FormField label="Email" name="email" type="email" autoComplete="email" required /><FormField label="Password" name="password" type="password" autoComplete="current-password" required /><button className="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white">Sign in</button></form><div className="mt-5 flex justify-between text-sm text-indigo-700"><Link to="/signup">Create account</Link><Link to="/forgot">Forgot password?</Link></div></section></main>;
}

function AuthPage({ title }: { title: string }) { return <main className="grid min-h-screen place-items-center p-6"><section className="w-full max-w-md rounded-2xl bg-white p-8 shadow-sm"><h1 className="text-2xl font-semibold">{title}</h1><p className="mt-2 text-sm text-slate-500">This form will connect to the Revo auth API in the authentication milestone.</p><Link className="mt-5 inline-block text-sm text-indigo-700" to="/login">Back to sign in</Link></section></main>; }

export const routes = [
  { path: "/login", element: <LoginPage /> },
  { path: "/signup", element: <AuthPage title="Create your account" /> },
  { path: "/forgot", element: <AuthPage title="Reset your password" /> },
  { path: "/reset", element: <AuthPage title="Choose a new password" /> },
];
