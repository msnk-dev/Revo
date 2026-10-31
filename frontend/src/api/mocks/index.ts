import type { Invoice, Payment, RevenuePoint, SessionUser, Subscription, Summary } from "../models";
import type { Page } from "../types";

const seedDate = "2026-10-31";
type DemoInvoice = Invoice & { period_start: string; period_end: string; lines: import("../models").InvoiceLine[] };
type DemoCustomer = { id: number; user_id: number | null; name: string; email: string; phone: string | null; company: string | null; billing_address: string | null; tax_id: string | null; is_active: boolean };
type DemoProduct = { id: number; name: string; type: "service" | "software" | "addon" | "physical"; sales_price: string; cost_price: string; notes: string | null; default_tax_id: number | null; is_active: boolean };
type DemoPlan = { id: number; name: string; price: string; billing_period: "daily" | "weekly" | "monthly" | "yearly"; min_quantity: number; available_from: string | null; available_to: string | null; auto_close: boolean; closable: boolean; pausable: boolean; renewable: boolean; is_active: boolean };
const customers: DemoCustomer[] = [{ id: 1, user_id: 2, name: "Demo Customer", email: "customer@revo.local", phone: "+91 98765 43210", company: "Brightloop Demo", billing_address: "Bengaluru, India", tax_id: "GST-DEMO", is_active: true }];
const products: DemoProduct[] = [{ id: 1, name: "Revo Subscription", type: "software", sales_price: "1200.00", cost_price: "0.00", notes: "Monthly software plan", default_tax_id: 1, is_active: true }];
const plans: DemoPlan[] = [{ id: 1, name: "Monthly", price: "1200.00", billing_period: "monthly", min_quantity: 1, available_from: null, available_to: null, auto_close: false, closable: true, pausable: true, renewable: true, is_active: true }, { id: 2, name: "Annual Support", price: "18000.00", billing_period: "yearly", min_quantity: 1, available_from: null, available_to: null, auto_close: false, closable: true, pausable: true, renewable: true, is_active: true }];
const taxes = [{ id: 1, name: "GST 18%", rate_pct: "18.00", is_active: true }];
const paymentMethods = [{ id: 1, name: "cash", is_active: true }, { id: 2, name: "bank_transfer", is_active: true }, { id: 3, name: "card", is_active: true }, { id: 4, name: "upi", is_active: true }, { id: 5, name: "cheque", is_active: true }];
const templates = [{ id: 1, name: "Monthly Software", plan_id: 1, validity_days: 30, lines: [{ product_id: 1, quantity: 1, variant_value_ids: [1] }] }];
let currentUser: SessionUser | null = null;
let subscriptions: Subscription[] = [
  {
    id: 1, number: "SUB-000001", customer_id: 1, customer_name: "Brightloop Demo", plan_id: 1,
    plan_name: "Monthly Software", billing_period: "monthly", status: "active", start_date: "2026-09-01",
    expiry_date: null, next_invoice_date: "2026-10-31", is_paused: false, pausable: true, closable: true, renewable: true, monthly_value: "1760.00",
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
let invoices: DemoInvoice[] = [
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
let staff: { id: number; name: string; email: string; role: "admin" | "staff"; is_active: boolean }[] = [{ id: 1, name: "Demo Admin", email: "admin@revo.local", role: "admin", is_active: true }];

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
    currentUser = { id: customer ? 2 : 1, name: customer ? "Demo Customer" : "Demo Admin", email: String(body.email).toLowerCase(), role: customer ? "customer" : "admin", customer_id: customer ? 1 : null };
    return reply(currentUser);
  }
  if (route === "/auth/signup" && method === "POST") {
    currentUser = { id: 2, name: String(body.name ?? "Demo Customer"), email: String(body.email ?? "customer@revo.local"), role: "customer", customer_id: 1 };
    return reply({ created: true });
  }
  if (route === "/auth/logout" && method === "POST") { currentUser = null; return reply(undefined); }
  if (["/auth/forgot", "/auth/reset"].includes(route) && method === "POST") return reply({ accepted: true });

  if (route === "/customers" && method === "GET") return reply(pageOf(customers.filter((item) => item.is_active), path));
  if (route === "/customers" && method === "POST") {
    const item: DemoCustomer = { id: Math.max(0, ...customers.map((row) => row.id)) + 1, user_id: null, name: String(body.name), email: String(body.email), phone: body.phone ? String(body.phone) : null, company: body.company ? String(body.company) : null, billing_address: body.billing_address ? String(body.billing_address) : null, tax_id: body.tax_id ? String(body.tax_id) : null, is_active: true };
    customers.unshift(item); return reply(item);
  }
  const customerMatch = /^\/customers\/(\d+)$/.exec(route);
  if (customerMatch) {
    const item = customers.find((row) => row.id === Number(customerMatch[1]));
    if (!item) throw new Error("Customer not found");
    if (method === "GET") return reply(item);
    if (method === "PUT") { Object.assign(item, body); return reply(item); }
    if (method === "DELETE") { item.is_active = false; return reply(undefined); }
  }
  if (route === "/products" && method === "GET") return reply(pageOf(products, path));
  if (route === "/products" && method === "POST") {
    const item: DemoProduct = { id: Math.max(0, ...products.map((row) => row.id)) + 1, name: String(body.name), type: body.type as DemoProduct["type"], sales_price: String(body.sales_price), cost_price: String(body.cost_price ?? "0.00"), notes: body.notes ? String(body.notes) : null, default_tax_id: body.default_tax_id ? Number(body.default_tax_id) : null, is_active: true };
    products.unshift(item); return reply(item);
  }
  const productMatch = /^\/products\/(\d+)$/.exec(route);
  if (productMatch && method === "DELETE") { const item = products.find((row) => row.id === Number(productMatch[1])); if (item) item.is_active = false; return reply(undefined); }
  if (route === "/plans" && method === "GET") return reply(pageOf(plans, path));
  if (route === "/plans" && method === "POST") {
    const item: DemoPlan = { id: Math.max(0, ...plans.map((row) => row.id)) + 1, name: String(body.name), price: String(body.price), billing_period: body.billing_period as DemoPlan["billing_period"], min_quantity: Number(body.min_quantity ?? 1), available_from: null, available_to: null, auto_close: Boolean(body.auto_close), closable: Boolean(body.closable), pausable: Boolean(body.pausable), renewable: Boolean(body.renewable), is_active: true };
    plans.unshift(item); return reply(item);
  }
  const planMatch = /^\/plans\/(\d+)$/.exec(route);
  if (planMatch && method === "DELETE") { const item = plans.find((row) => row.id === Number(planMatch[1])); if (item) item.is_active = false; return reply(undefined); }
  if (route === "/taxes" && method === "GET") return reply(pageOf(taxes, path));
  if (route === "/taxes" && method === "POST") { const item = { id: Math.max(0, ...taxes.map((row) => row.id)) + 1, name: String(body.name), rate_pct: String(body.rate_pct), is_active: true }; taxes.unshift(item); return reply(item); }
  if (route === "/payment-methods" && method === "GET") return reply(pageOf(paymentMethods, path));
  if (route === "/quotation-templates" && method === "GET") return reply(pageOf(templates, path));
  if (route === "/admin/staff" && method === "GET") return reply(pageOf(staff, path));
  if (route === "/admin/staff" && method === "POST") { const item = { id: Math.max(0, ...staff.map((row) => row.id)) + 1, name: String(body.name), email: String(body.email), role: "staff" as const, is_active: true }; staff.unshift(item); return reply(item); }
  const staffMatch = /^\/admin\/staff\/(\d+)$/.exec(route);
  if (staffMatch && method === "PATCH") { const item = staff.find((row) => row.id === Number(staffMatch[1])); if (item) item.is_active = false; return reply(item); }

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
  if (route === "/reports/overdue") return reply(invoices.filter((invoice) => invoice.status === "confirmed" && invoice.amount_due !== "0.00" && invoice.due_date < seedDate).slice(0, Number(url.searchParams.get("limit") ?? 50)).map((invoice) => ({ invoice_id: invoice.id, invoice_number: invoice.number, customer_name: invoice.customer_name, due_date: invoice.due_date, days_overdue: Math.max(0, Math.floor((Date.parse(`${seedDate}T00:00:00Z`) - Date.parse(`${invoice.due_date}T00:00:00Z`)) / 86400000)), amount_due: invoice.amount_due })));
  if (route === "/reports/overdue/summary") { const rows = invoices.filter((invoice) => invoice.status === "confirmed" && invoice.amount_due !== "0.00" && invoice.due_date < seedDate); return reply({ count: rows.length, amount_due: centsToDecimal(rows.reduce((sum, row) => sum + decimalToCents(row.amount_due), 0n)) }); }
  if (route === "/reports/subscriptions") return reply({ active: subscriptions.filter((item) => item.status === "active" && !item.is_paused).length, paused: subscriptions.filter((item) => item.is_paused).length, by_plan: { "Monthly Software": 1, "Annual Support": 1 } });
  if (route === "/reports/payments") {
    const rows = payments.map((payment) => ({ ...payment, invoice_number: invoices.find((invoice) => invoice.id === payment.invoice_id)?.number ?? `INV-${payment.invoice_id}`, customer_name: customers.find((customer) => customer.id === invoices.find((invoice) => invoice.id === payment.invoice_id)?.customer_id)?.name ?? "Demo Customer" }));
    const page = pageOf(rows, path); return reply({ ...page, amount: centsToDecimal(rows.reduce((sum, row) => sum + decimalToCents(row.amount), 0n)) });
  }
  if (route === "/ai/brief/latest" && method === "GET") return reply({ brief_date: seedDate, payload: {}, narrative: "Daily CFO brief: current MRR is INR 3,260.00; collected today is INR 21,240.00. This local demo summary is deterministic.", model: null, provider: null, used_fallback: true });
  if (route === "/ai/brief/generate" && method === "POST") return reply({ brief_date: seedDate, payload: {}, narrative: "Daily CFO brief: current MRR is INR 3,260.00; collected today is INR 21,240.00. This local demo summary is deterministic.", model: null, provider: null, used_fallback: true });

  if (route === "/subscriptions" && method === "POST") {
    const id = Math.max(0, ...subscriptions.map((item) => item.id)) + 1; const plan = plans.find((item) => item.id === Number(body.plan_id)); const product = products.find((item) => item.id === Number((body.lines as { product_id: number }[])?.[0]?.product_id)); const customer = customers.find((item) => item.id === Number(body.customer_id));
    if (!plan || !product || !customer) throw new Error("Choose an existing customer, plan, and product");
    const lineInput = (body.lines as { quantity: number }[])[0]; const item: Subscription = { id, number: `SUB-${String(id).padStart(6, "0")}`, customer_id: customer.id, customer_name: customer.name, plan_id: plan.id, plan_name: plan.name, billing_period: plan.billing_period, status: "draft", start_date: String(body.start_date), expiry_date: body.expiry_date ? String(body.expiry_date) : null, next_invoice_date: String(body.start_date), is_paused: false, pausable: plan.pausable, closable: plan.closable, renewable: plan.renewable, monthly_value: plan.price, lines: [{ id: 1, product_id: product.id, description: product.name, quantity: Number(lineInput.quantity), unit_price: product.sales_price, tax_id: product.default_tax_id, variant_value_ids: [] }], history: [{ id: 1, from_status: null, to_status: "draft", changed_at: new Date().toISOString(), changed_by: currentUser?.id ?? 1 }] };
    subscriptions.unshift(item); return reply(item);
  }
  const templateMatch = /^\/subscriptions\/from-template\/(\d+)$/.exec(route);
  if (templateMatch && method === "POST") {
    const template = templates.find((item) => item.id === Number(templateMatch[1])); const customer = customers.find((item) => item.id === Number(body.customer_id)); const plan = plans.find((item) => item.id === template?.plan_id); const product = products.find((item) => item.id === template?.lines[0].product_id);
    if (!template || !customer || !plan || !product) throw new Error("Template data is unavailable");
    const id = Math.max(0, ...subscriptions.map((item) => item.id)) + 1; const item: Subscription = { id, number: `SUB-${String(id).padStart(6, "0")}`, customer_id: customer.id, customer_name: customer.name, plan_id: plan.id, plan_name: plan.name, billing_period: plan.billing_period, status: "quotation", start_date: String(body.start_date), expiry_date: null, quotation_expires_on: seedDate, next_invoice_date: null, is_paused: false, pausable: plan.pausable, closable: plan.closable, renewable: plan.renewable, monthly_value: plan.price, lines: [{ id: 1, product_id: product.id, description: product.name, quantity: template.lines[0].quantity, unit_price: product.sales_price, tax_id: product.default_tax_id, variant_value_ids: template.lines[0].variant_value_ids }], history: [{ id: 1, from_status: null, to_status: "quotation", changed_at: new Date().toISOString(), changed_by: currentUser?.id ?? 1 }] };
    subscriptions.unshift(item); return reply(item);
  }
  if (["/subscriptions", "/portal/subscriptions"].includes(route)) {
    const rows = route.startsWith("/portal") ? subscriptions.filter((item) => item.customer_id === currentUser?.customer_id) : subscriptions;
    return reply(pageOf(rows, path));
  }
  if (route === "/invoices/generate" && method === "POST") {
    const due = subscriptions.filter((item) => item.status === "active" && !item.is_paused && item.next_invoice_date && item.next_invoice_date <= (url.searchParams.get("as_of") ?? seedDate) && !invoices.some((invoice) => invoice.subscription_id === item.id && invoice.period_start === item.next_invoice_date));
    if (url.searchParams.get("dry_run") === "true") return reply({ dry_run: true, as_of: url.searchParams.get("as_of") ?? seedDate, eligible_count: due.length, failed: [] });
    for (const subscription of due) {
      const product = products.find((item) => item.id === subscription.lines[0]?.product_id); const tax = taxes.find((item) => item.id === product?.default_tax_id); const subtotal = subscription.lines.reduce((sum, line) => sum + decimalToCents(line.unit_price) * BigInt(line.quantity), 0n); const taxAmount = tax ? subtotal * decimalToCents(tax.rate_pct) / 10000n : 0n; const total = subtotal + taxAmount; const id = Math.max(0, ...invoices.map((item) => item.id)) + 1;
      invoices.unshift({ id, number: `INV-${String(id).padStart(6, "0")}`, subscription_id: subscription.id, customer_id: subscription.customer_id, customer_name: subscription.customer_name, status: "draft", invoice_date: seedDate, due_date: seedDate, period_start: subscription.next_invoice_date ?? seedDate, period_end: seedDate, subtotal: centsToDecimal(subtotal), discount_total: "0.00", tax_total: centsToDecimal(taxAmount), total: centsToDecimal(total), amount_paid: "0.00", amount_due: centsToDecimal(total), lines: subscription.lines.map((line) => ({ description: line.description, quantity: line.quantity, unit_price: line.unit_price, variant_extra: "0.00", discount_name: null, discount_amount: "0.00", discount_reason: null, tax_name: tax?.name ?? null, tax_rate_pct: tax?.rate_pct ?? null, tax_amount: centsToDecimal(taxAmount), line_total: centsToDecimal(total) })) });
      subscription.next_invoice_date = seedDate;
    }
    return reply({ dry_run: false, as_of: url.searchParams.get("as_of") ?? seedDate, created: due.length, skipped_duplicates: 0, failed: [] });
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
    return reply({ invoice_id: invoice.id, invoice_number: invoice.number, lines: invoice.lines, subtotal: invoice.subtotal, discount_total: invoice.discount_total, tax_total: invoice.tax_total, total: invoice.total });
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
    return reply({ subscription: renewed });
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
    const methodId = Number(body.method_id ?? 2); const method = paymentMethods.find((entry) => entry.id === methodId)?.name ?? "bank_transfer";
    const payment: Payment = { id: nextPaymentId++, invoice_id: item.id, invoice_number: item.number, customer_name: item.customer_name, amount, paid_on: String(body.paid_on ?? seedDate), method, note: String(body.note ?? "") };
    payments = [payment, ...payments];
    return reply(payment);
  }
  if (route === "/ai/chat" && method === "POST") {
    return reply({ answer: "Demo assistant: I can help explain Revo data once the backend AI tools are connected.", proposals: [], thread_id: "demo-thread" });
  }
  throw new Error(`No demo response configured for ${method} ${route}`);
}
