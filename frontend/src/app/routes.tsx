import type { RouteObject } from "react-router-dom";
import { routes as authRoutes } from "../features/auth";
import { routes as dashboardRoutes } from "../features/dashboard";
import { routes as subscriptionRoutes } from "../features/subscriptions";
import { routes as invoiceRoutes } from "../features/invoices";
import { routes as paymentRoutes } from "../features/payments";
import { routes as portalRoutes } from "../features/portal";
import { routes as aiRoutes } from "../features/ai";
import { routes as catalogRoutes } from "../features/catalog";
import { routes as customerRoutes } from "../features/customers";
import { routes as reportRoutes } from "../features/reports";
import { routes as staffRoutes } from "../features/staff";
import { Layout } from "./Layout";
import { RoleGuard } from "./RoleGuard";

export const appRoutes: RouteObject[] = [
  ...authRoutes,
  {
    element: <RoleGuard />,
    children: [{
      element: <Layout />,
      children: [
        ...dashboardRoutes,
        ...subscriptionRoutes,
        ...invoiceRoutes,
        ...paymentRoutes,
        ...portalRoutes,
        ...aiRoutes,
        ...catalogRoutes,
        ...customerRoutes,
        ...reportRoutes,
        ...staffRoutes,
      ],
    }],
  },
];
