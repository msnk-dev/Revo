import { NavLink, Outlet } from "react-router-dom";
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

const allNav: NavItem[] = [...dashboardNav, ...customerNav, ...subscriptionNav, ...invoiceNav, ...paymentNav, ...reportNav, ...catalogNav, ...staffNav, ...portalNav, ...aiNav, ...authNav];

export function Layout() {
  const { user } = useAuth();
  const visibleNav = allNav.filter((item) => !item.roles || (user && item.roles.includes(user.role)));
  return (
    <div className="min-h-screen md:flex">
      <aside className="w-full border-b border-slate-200 bg-white p-5 md:min-h-screen md:w-64 md:border-b-0 md:border-r">
        <NavLink to="/" className="text-xl font-bold tracking-tight text-indigo-700">revo<span className="text-slate-400">.</span></NavLink>
        <p className="mt-1 text-xs text-slate-500">Subscription management</p>
        <nav className="mt-8 flex gap-2 overflow-auto md:flex-col">
          {visibleNav.map((item) => <NavLink key={item.path} to={item.path} className={({ isActive }) => `whitespace-nowrap rounded-lg px-3 py-2 text-sm ${isActive ? "bg-indigo-50 font-semibold text-indigo-700" : "text-slate-600 hover:bg-slate-50"}`}>{item.label}</NavLink>)}
        </nav>
      </aside>
      <main className="min-w-0 flex-1 p-5 md:p-9"><Outlet /></main>
    </div>
  );
}
