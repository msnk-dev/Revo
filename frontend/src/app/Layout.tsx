import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext";
import type { NavItem } from "./navigation";
import { nav as authNav } from "../features/auth/nav";
import { nav as dashboardNav } from "../features/dashboard/nav";
import { nav as subscriptionNav } from "../features/subscriptions/nav";
import { nav as invoiceNav } from "../features/invoices/nav";
import { nav as paymentNav } from "../features/payments/nav";
import { nav as portalNav } from "../features/portal/nav";
import { nav as aiNav } from "../features/ai/nav";
import { nav as catalogNav } from "../features/catalog/nav";
import { nav as customerNav } from "../features/customers/nav";
import { nav as reportNav } from "../features/reports/nav";
import { nav as staffNav } from "../features/staff/nav";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AssistantPanel } from "../features/ai/AssistantPanel";

const allNav: NavItem[] = [...dashboardNav, ...customerNav, ...subscriptionNav, ...invoiceNav, ...paymentNav, ...reportNav, ...catalogNav, ...staffNav, ...portalNav, ...aiNav, ...authNav];

export function Layout() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [assistantOpen, setAssistantOpen] = useState(false);
  const visibleNav = allNav.filter((item) => !item.roles || (user && item.roles.includes(user.role)));
  const groups = [
    { label: "Overview", items: visibleNav.filter((item) => item.path === "/") },
    { label: "Workspace", items: visibleNav.filter((item) => ["/customers", "/catalog", "/staff", "/reports"].includes(item.path)) },
    { label: "Billing", items: visibleNav.filter((item) => ["/subscriptions", "/invoices", "/payments"].includes(item.path)) },
    { label: "Account", items: visibleNav.filter((item) => ["/portal", "/assistant"].includes(item.path)) },
  ].filter((group) => group.items.length > 0);
  const active = [...allNav].filter((item) => location.pathname === item.path || (item.path !== "/" && location.pathname.startsWith(`${item.path}/`))).sort((a, b) => b.path.length - a.path.length)[0];
  const pageName = location.pathname.includes("/") && location.pathname.split("/").filter(Boolean).length > 1
    ? `${active?.label ?? "Details"} · ${location.pathname.split("/").filter(Boolean).at(-1)}`
    : active?.label ?? "Workspace";
  return (
    <div className="min-h-screen md:flex">
      <aside className="w-full border-b border-slate-200 bg-white p-5 md:min-h-screen md:w-64 md:border-b-0 md:border-r">
        <NavLink to="/" className="text-xl font-bold tracking-tight text-indigo-700">revo<span className="text-slate-400">.</span></NavLink>
        <p className="mt-1 text-xs text-slate-500">Subscription management</p>
        <nav aria-label="Main navigation" className="mt-8 flex gap-5 overflow-auto md:flex-col">
          {groups.map((group) => <div key={group.label} className="flex shrink-0 gap-1 md:flex-col">
            <p className="hidden px-3 pb-1 text-[10px] font-semibold uppercase tracking-widest text-slate-400 md:block">{group.label}</p>
            {group.items.map((item) => <NavLink key={item.path} to={item.path} end={item.path === "/"} className={({ isActive }) => `whitespace-nowrap rounded-lg px-3 py-2 text-sm ${isActive ? "bg-indigo-50 font-semibold text-indigo-700" : "text-slate-600 hover:bg-slate-50"}`}>{item.label}</NavLink>)}
          </div>)}
        </nav>
      </aside>
      <div className="min-w-0 flex-1">
        <header className="flex items-center justify-end gap-3 border-b border-slate-200 bg-white px-5 py-3 md:px-9">
          {import.meta.env.VITE_USE_MOCKS === "true" && <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-800">Demo mode</span>}
          <button onClick={() => setAssistantOpen(true)} className="rounded-lg border border-indigo-200 px-3 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-50">Ask Revo AI</button>
          <span className="hidden text-sm text-slate-600 sm:inline">{user?.name}</span>
          <button onClick={async () => { await signOut(); navigate("/login"); }} className="rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-100">Sign out</button>
        </header>
        <main className="min-w-0 p-5 md:p-9">
          <nav aria-label="Breadcrumb" className="mx-auto mb-6 max-w-7xl text-xs text-slate-500"><NavLink to={user?.role === "customer" ? "/portal" : "/"} className="hover:text-indigo-700">Home</NavLink><span className="mx-2 text-slate-300">/</span><span aria-current="page" className="font-medium text-slate-700">{pageName}</span></nav>
          <Outlet />
        </main>
      </div>
      <AssistantPanel open={assistantOpen} onClose={() => setAssistantOpen(false)} />
    </div>
  );
}
