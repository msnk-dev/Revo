import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
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
  const pageName = location.pathname.split("/").filter(Boolean).length > 1
    ? `${active?.label ?? "Details"} · ${location.pathname.split("/").filter(Boolean).at(-1)}`
    : active?.label ?? "Workspace";
  const initials = (user?.name ?? "Revo").split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();

  return (
    <div className="min-h-screen md:flex">
      <aside className="revo-sidebar relative z-10 w-full overflow-hidden border-b border-white/10 lg:sticky lg:top-0 lg:h-screen lg:w-[17rem] lg:shrink-0 lg:border-b-0 lg:border-r lg:border-white/10">
        <div className="relative flex items-center justify-between px-5 pb-3 pt-5 lg:block lg:px-6 lg:pb-5 lg:pt-7">
          <NavLink to={user?.role === "customer" ? "/portal" : "/"} className="inline-flex items-center gap-3">
            <span className="block text-2xl font-bold tracking-tight text-white">revo<span className="text-[#b3d57d]">.</span></span>
          </NavLink>
          <span className="text-sm capitalize text-white/70 lg:hidden">{user?.role ?? "Workspace"}</span>
        </div>
        <nav aria-label="Main navigation" className="relative flex gap-4 overflow-x-auto px-3 pb-3 lg:mt-5 lg:block lg:space-y-6 lg:overflow-y-auto lg:px-4 lg:pb-6">
          {groups.map((group) => <div key={group.label} className="shrink-0 lg:space-y-1">
            <p className="hidden px-3 pb-1 text-[13px] font-semibold text-white/55 lg:block">{group.label}</p>
            <div className="flex gap-1 lg:flex-col">{group.items.map((item) => <NavLink key={item.path} to={item.path} end={item.path === "/"} className={({ isActive }) => `revo-nav-link flex items-center whitespace-nowrap rounded-sm px-3 py-2.5 text-sm font-medium ${isActive ? "text-white" : "text-white/70 hover:bg-white/5 hover:text-white"}`}>
              {item.label}
            </NavLink>)}</div>
          </div>)}
        </nav>
        <div className="relative mx-6 mb-6 mt-2 hidden border-t border-white/15 pt-4 lg:block">
          <p className="text-sm font-semibold text-white">Brightloop Software</p><p className="mt-1 text-sm leading-5 text-white/65">Revenue operations workspace.</p>
        </div>
      </aside>
      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-20 flex min-h-[4.5rem] items-center justify-between gap-4 border-b border-slate-300 bg-white px-4 sm:px-6 lg:px-9">
          <div className="min-w-0"><p className="truncate text-base font-semibold text-slate-800">{pageName}</p></div>
          <div className="flex shrink-0 items-center gap-2 sm:gap-3">
            {import.meta.env.VITE_USE_MOCKS === "true" && <span className="hidden rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-[10px] font-semibold text-amber-800 sm:inline-flex">Preview mode</span>}
            <button onClick={() => setAssistantOpen(true)} className="inline-flex items-center gap-2 px-2 py-2 text-sm font-medium text-slate-600 transition hover:text-indigo-700"><span className="hidden sm:inline">Ask Revo AI</span><span className="sm:hidden">AI</span></button>
            <div className="hidden items-center gap-2 border-l border-slate-200 pl-3 sm:flex"><span className="grid h-8 w-8 place-items-center rounded-sm bg-slate-100 text-xs font-semibold text-slate-800">{initials}</span><span className="max-w-36 truncate text-sm font-medium text-slate-700">{user?.name}</span></div>
            <button onClick={async () => { await signOut(); navigate("/login"); }} className="px-2.5 py-2 text-sm font-medium text-slate-500 transition hover:text-rose-700 sm:px-3">Sign out</button>
          </div>
        </header>
        <main className="revo-workspace-main min-w-0 px-4 pb-10 pt-5 sm:px-6 sm:pt-7 lg:px-9 lg:pt-8">
          <nav aria-label="Breadcrumb" className="mx-auto mb-5 max-w-7xl text-[11px] text-slate-400"><NavLink to={user?.role === "customer" ? "/portal" : "/"} className="transition hover:text-indigo-700">Workspace</NavLink><span className="mx-2 text-slate-300">/</span><span aria-current="page" className="font-semibold text-slate-600">{pageName}</span></nav>
          <Outlet />
        </main>
      </div>
      <AssistantPanel open={assistantOpen} onClose={() => setAssistantOpen(false)} />
    </div>
  );
}
