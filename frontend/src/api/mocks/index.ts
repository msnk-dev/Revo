import type { Invoice, Payment, RevenuePoint, SessionUser, Subscription, Summary } from "../models";
import type { Page } from "../types";

const seedDate = "2026-10-31";
let currentUser: SessionUser | null = null;
let subscriptions: Subscription[] = [
  {
    id: 1, number: "SUB-000001", customer_id: 1, customer_name: "Brightloop Demo", plan_id: 1,
    plan_name: "Monthly Software", billing_period: "monthly", status: "active", start_date: "2026-09-01",
    expiry_date: null, next_invoice_date: "2026-11-01", is_paused: false, pausable: true, closable: true, renewable: true, monthly_value: "1760.00",
    lines: [{ description: "Revo Subscription · Brand: Odoo", quantity: 1, unit_price: "1760.00" }],
    history: [{ from_status: "confirmed", to_status: "active", changed_at: "2026-09-01T00:05:00Z", changed_by: "System" }],
  },
  {
    id: 2, number: "SUB-000002", customer_id: 1, customer_name: "Brightloop Demo", plan_id: 2,
    plan_name: "Annual Support", billing_period: "yearly", status: "active", start_date: "2026-02-15",
    expiry_date: "2027-02-14", next_invoice_date: "2027-02-15", is_paused: false, pausable: true, closable: true, renewable: true, monthly_value: "1500.00",
    lines: [{ description: "Priority support", quantity: 1, unit_price: "18000.00" }],
    history: [{ from_status: "confirmed", to_status: "active", changed_at: "2026-02-15T00:05:00Z", changed_by: "System" }],
  },
];
let invoices: Invoice[] = [
  {
    id: 1, number: "INV-000001", subscription_id: 1, customer_id: 1, customer_name: "Brightloop Demo",
    status: "confirmed", invoice_date: "2026-10-01", due_date: "2026-10-15", period_start: "2026-10-01",
    period_end: "2026-10-31", subtotal: "1760.00", discount_total: "0.00", tax_total: "316.80",
    total: "2076.80", amount_paid: "0.00", amount_due: "2076.80",
    lines: [{ description: "Revo Subscription · Brand: Odoo", quantity: 1, unit_price: "1760.00", variant_extra: "560.00", discount_name: null, discount_amount: "0.00", discount_reason: null, tax_name: "GST 18%", tax_rate_pct: "18.00", tax_amount: "316.80", line_total: "2076.80" }],
  },
  {
    id: 2, number: "INV-000002", subscription_id: 2, customer_id: 1, customer_name: "Brightloop Demo",
    status: "paid", invoice_date: "2026-10-15", due_date: "2026-10-29", period_start: "2026-02-15",
    period_end: "2027-02-14", subtotal: "18000.00", discount_total: "0.00", tax_total: "3240.00",
    total: "21240.00", amount_paid: "21240.00", amount_due: "0.00",
    lines: [{ description: "Priority support", quantity: 1, unit_price: "18000.00", variant_extra: "0.00", discount_name: null, discount_amount: "0.00", discount_reason: null, tax_name: "GST 18%", tax_rate_pct: "18.00", tax_amount: "3240.00", line_total: "21240.00" }],
  },
  {
    id: 3, number: "INV-000003", subscription_id: 1, customer_id: 1, customer_name: "Brightloop Demo",
    status: "draft", invoice_date: "2026-10-31", due_date: "2026-11-14", period_start: "2026-11-01",
    period_end: "2026-11-30", subtotal: "1760.00", discount_total: "0.00", tax_total: "316.80",
    total: "2076.80", amount_paid: "0.00", amount_due: "2076.80",
    lines: [{ description: "Revo Subscription · Brand: Odoo", quantity: 1, unit_price: "1760.00", variant_extra: "560.00", discount_name: null, discount_amount: "0.00", discount_reason: null, tax_name: "GST 18%", tax_rate_pct: "18.00", tax_amount: "316.80", line_total: "2076.80" }],
  },
];
let payments: Payment[] = [{ id: 1, invoice_id: 2, invoice_number: "INV-000002", customer_name: "Brightloop Demo", amount: "21240.00", paid_on: "2026-10-15", method: "bank_transfer", note: "Demo payment" }];
let nextPaymentId = 2;

function pageOf<T>(items: T[], path: string): Page<T> {
  const url = new URL(path, "http://mock.local");
  const page = Math.max(1, Number(url.searchParams.get("page") ?? 1));
  const pageSize = Math.min(100, Math.max(1, Number(url.searchParams.get("page_size") ?? 20)));
  const status = url.searchParams.get("status"); const search = url.searchParams.get("q")?.toLowerCase();
  const filtered = items.filter((item) => {
    const record = item as { status?: string };
    return (!status || record.status === status) && (!search || JSON.stringify(item).toLowerCase().includes(search));
  });
  return { items: filtered.slice((page - 1) * pageSize, page * pageSize), total: filtered.length, page, page_size: pageSize };
}

function decimalToCents(value: string): bigint {
  const match = /^(-?\d+)(?:\.(\d{0,2}))?$/.exec(value);
  if (!match) throw new Error("Enter an amount with up to two decimal places");
  const [, major = "0", minor = ""] = match;
  return BigInt(major) * 100n + BigInt(minor.padEnd(2, "0"));
}

function centsToDecimal(value: bigint): string {
  const sign = value < 0n ? "-" : "";
  const absolute = value < 0n ? -value : value;
  return `${sign}${absolute / 100n}.${String(absolute % 100n).padStart(2, "0")}`;
}

export async function mockRequest<T>(path: string, init?: RequestInit): Promise<T> {
  await new Promise((resolve) => setTimeout(resolve, 90));
  const url = new URL(path, "http://mock.local");
  const route = url.pathname;
  const method = init?.method ?? "GET";
  const body = init?.body ? JSON.parse(String(init.body)) as Record<string, unknown> : {};
  const reply = (value: unknown) => value as T;

  if (route === "/auth/me" && method === "GET") return reply(currentUser);
  if (route === "/auth/login" && method === "POST") {
    if (typeof body.email !== "string" || typeof body.password !== "string" || !body.password) throw new Error("Enter your email and password");
    const customer = body.email.toLowerCase().includes("customer");
    currentUser = { id: customer ? 2 : 1, name: customer ? "Demo Customer" : "Demo Admin", role: customer ? "customer" : "admin", customer_id: customer ? 1 : null };
    return reply(currentUser);
  }
  if (route === "/auth/signup" && method === "POST") {
    currentUser = { id: 2, name: String(body.name ?? "Demo Customer"), role: "customer", customer_id: 1 };
    return reply({ created: true });
  }
  if (route === "/auth/logout" && method === "POST") { currentUser = null; return reply(undefined); }
  if (["/auth/forgot", "/auth/reset"].includes(route) && method === "POST") return reply({ accepted: true });

  if (route === "/reports/summary") {
    const active = subscriptions.filter((item) => item.status === "active");
    const collectible = invoices.filter((item) => item.status === "confirmed");
    const billed = invoices.filter((item) => item.status === "confirmed" || item.status === "paid");
    const overdueItems = collectible.filter((item) => item.amount_due !== "0.00" && item.due_date < seedDate);
    const summary: Summary = {
      active_subscriptions: active.length,
      paused_subscriptions: subscriptions.filter((item) => item.is_paused).length,
      mrr: centsToDecimal(active.filter((item) => !item.is_paused).reduce((sum, item) => sum + decimalToCents(item.monthly_value), 0n)),
      collected: centsToDecimal(payments.reduce((sum, item) => sum + decimalToCents(item.amount), 0n)),
      invoiced: centsToDecimal(billed.reduce((sum, item) => sum + decimalToCents(item.total), 0n)),
      outstanding: centsToDecimal(collectible.reduce((sum, item) => sum + decimalToCents(item.amount_due), 0n)),
      overdue_count: overdueItems.length,
    };
    return reply(summary);
  }
  if (route === "/reports/revenue") {
    const revenue: RevenuePoint[] = [
      { month: "2026-05-01", revenue_collected: "0.00", invoiced: "0.00" },
      { month: "2026-06-01", revenue_collected: "0.00", invoiced: "0.00" },
      { month: "2026-07-01", revenue_collected: "0.00", invoiced: "0.00" },
      { month: "2026-08-01", revenue_collected: "0.00", invoiced: "0.00" },
      { month: "2026-09-01", revenue_collected: "0.00", invoiced: "0.00" },
      { month: "2026-10-01", revenue_collected: centsToDecimal(payments.reduce((sum, item) => sum + decimalToCents(item.amount), 0n)), invoiced: centsToDecimal(invoices.filter((item) => item.invoice_date.startsWith("2026-10") && (item.status === "confirmed" || item.status === "paid")).reduce((sum, item) => sum + decimalToCents(item.total), 0n)) },
    ];
    return reply(revenue);
  }
  if (route === "/reports/overdue") return reply(pageOf(invoices.filter((invoice) => invoice.status === "confirmed" && invoice.amount_due !== "0.00" && invoice.due_date < seedDate), path));

  if (["/subscriptions", "/portal/subscriptions"].includes(route)) {
    const rows = route.startsWith("/portal") ? subscriptions.filter((item) => item.customer_id === currentUser?.customer_id) : subscriptions;
    return reply(pageOf(rows, path));
  }
  if (["/invoices", "/portal/invoices"].includes(route)) {
    const rows = route.startsWith("/portal") ? invoices.filter((item) => item.customer_id === currentUser?.customer_id) : invoices;
    return reply(pageOf(rows, path));
  }
  if (["/payments", "/portal/payments"].includes(route)) {
    const rows = route.startsWith("/portal") ? payments.filter((item) => invoices.some((invoice) => invoice.id === item.invoice_id && invoice.customer_id === currentUser?.customer_id)) : payments;
    return reply(pageOf(rows, path));
  }
  const invoiceMatch = /^\/(?:portal\/)?invoices\/(\d+)$/.exec(route);
  if (invoiceMatch && method === "GET") {
    const invoice = invoices.find((item) => item.id === Number(invoiceMatch[1]));
    if (!invoice || (route.startsWith("/portal") && invoice.customer_id !== currentUser?.customer_id)) throw new Error("Invoice not found");
    return reply(invoice);
  }
  const subscriptionMatch = /^\/subscriptions\/(\d+)$/.exec(route);
  if (subscriptionMatch && method === "GET") {
    const subscription = subscriptions.find((item) => item.id === Number(subscriptionMatch[1]));
    if (!subscription) throw new Error("Subscription not found");
    return reply(subscription);
  }
  const subscriptionAction = /^\/subscriptions\/(\d+)\/(transition|pause|resume|close)$/.exec(route);
  if (subscriptionAction && method === "POST") {
    const item = subscriptions.find((sub) => sub.id === Number(subscriptionAction[1]));
    if (!item) throw new Error("Subscription not found");
    const fromStatus = item.status;
    if (subscriptionAction[2] === "transition") item.status = body.to as Subscription["status"];
    if (subscriptionAction[2] === "pause") item.is_paused = true;
    if (subscriptionAction[2] === "resume") item.is_paused = false;
    if (subscriptionAction[2] === "close") item.status = "closed";
    item.history.push({ from_status: fromStatus, to_status: item.status, changed_at: new Date().toISOString(), changed_by: currentUser?.name ?? "Demo User" });
    return reply(item);
  }
  const renewMatch = /^\/subscriptions\/(\d+)\/renew$/.exec(route);
  if (renewMatch && method === "POST") {
    const old = subscriptions.find((item) => item.id === Number(renewMatch[1]));
    if (!old || !old.renewable) throw new Error("Subscription cannot be renewed");
    const nextId = Math.max(...subscriptions.map((item) => item.id)) + 1;
    const nextDate = old.expiry_date ?? seedDate;
    const renewed: Subscription = { ...structuredClone(old), id: nextId, number: `SUB-${String(nextId).padStart(6, "0")}`, status: "draft", start_date: nextDate, expiry_date: null, next_invoice_date: nextDate, is_paused: false, history: [{ from_status: null, to_status: "draft", changed_at: new Date().toISOString(), changed_by: currentUser?.name ?? "Demo User" }] };
    subscriptions = [renewed, ...subscriptions];
    return reply(renewed);
  }
  const invoiceAction = /^\/invoices\/(\d+)\/(confirm|cancel|send)$/.exec(route);
  if (invoiceAction && method === "POST") {
    const item = invoices.find((invoice) => invoice.id === Number(invoiceAction[1]));
    if (!item) throw new Error("Invoice not found");
    if (invoiceAction[2] === "cancel" && (item.status === "paid" || decimalToCents(item.amount_paid) > 0n)) throw new Error("An invoice with payments cannot be cancelled");
    if (invoiceAction[2] === "confirm") item.status = "confirmed";
    if (invoiceAction[2] === "cancel") item.status = "cancelled";
    return reply({ accepted: true });
  }
  const paymentMatch = /^\/invoices\/(\d+)\/payments$/.exec(route);
  if (paymentMatch && method === "POST") {
    const item = invoices.find((invoice) => invoice.id === Number(paymentMatch[1]));
    if (!item || item.status !== "confirmed") throw new Error("This invoice cannot accept a payment");
    const amount = String(body.amount ?? "");
    const cents = decimalToCents(amount);
    if (cents <= 0n || cents > decimalToCents(item.amount_due)) throw new Error("Payment must be positive and cannot exceed the amount due");
    item.amount_paid = centsToDecimal(decimalToCents(item.amount_paid) + cents);
    item.amount_due = centsToDecimal(decimalToCents(item.total) - decimalToCents(item.amount_paid));
    if (item.amount_due === "0.00") item.status = "paid";
    const payment: Payment = { id: nextPaymentId++, invoice_id: item.id, invoice_number: item.number, customer_name: item.customer_name, amount, paid_on: String(body.paid_on ?? seedDate), method: String(body.method ?? "bank_transfer"), note: String(body.note ?? "") };
    payments = [payment, ...payments];
    return reply(payment);
  }
  if (route === "/ai/chat" && method === "POST") {
    return reply({ answer: "Demo assistant: I can help explain Revo data once the backend AI tools are connected.", proposals: [], thread_id: "demo-thread" });
  }
  throw new Error(`No demo response configured for ${method} ${route}`);
}
