import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest, ApiRequestError } from "../../api/client";
import type { Page } from "../../api/types";
import { DataTable, type Column } from "../../components/DataTable";
import { FormField } from "../../components/FormField";
import { Money } from "../../components/Money";
import { StatusChip } from "../../components/StatusChip";
import { ErrorState, LoadingState, Screen, primaryButton, secondaryButton } from "../../components/Screen";
import { RoleGuard } from "../../app/RoleGuard";

type Product = { id: number; name: string; type: "service" | "software" | "addon" | "physical"; sales_price: string; cost_price: string; notes: string | null; default_tax_id: number | null; is_active: boolean };
type Plan = { id: number; name: string; price: string; billing_period: "daily" | "weekly" | "monthly" | "yearly"; min_quantity: number; available_from: string | null; available_to: string | null; auto_close: boolean; closable: boolean; pausable: boolean; renewable: boolean; is_active: boolean };
type Tax = { id: number; name: string; rate_pct: string; is_active: boolean };
type PaymentMethod = { id: number; name: string; is_active: boolean };
type Discount = { id: number; name: string; type: "fixed" | "percent"; value: string; scope: "product" | "subscription"; min_purchase: string; min_quantity: number; start_date: string | null; end_date: string | null; max_uses: number | null; uses_count: number; is_active: boolean; product_ids: number[] };
type Template = { id: number; name: string; plan_id: number; validity_days: number; lines: { id: number; product_id: number; quantity: number; variant_value_ids: number[] }[] };
type VariantAttribute = { id: number; product_id: number; name: string; values: { id: number; value: string; extra_price: string }[] };
type Tab = "products" | "variants" | "plans" | "taxes" | "payments" | "discounts" | "templates";
type FieldErrors = Record<string, string>;

const tabs: { id: Tab; label: string }[] = [
  { id: "products", label: "Products" }, { id: "variants", label: "Product variants" }, { id: "plans", label: "Plans" },
  { id: "taxes", label: "Taxes" }, { id: "payments", label: "Payment methods" }, { id: "discounts", label: "Discounts" },
  { id: "templates", label: "Quotation templates" },
];
const pageSize = 10;
const controlClass = "mt-1.5 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm font-normal text-slate-800";
const labelClass = "block text-sm font-medium text-slate-700";
const moneyPattern = /^\d+(?:\.\d{1,2})?$/;

function nameError(value: string, max: number, label: string): string | undefined {
  const trimmed = value.trim();
  if (!trimmed) return `${label} is required.`;
  if (trimmed.length > max) return `Use at most ${max} characters.`;
  return undefined;
}
function amountError(value: string, allowZero = true): string | undefined {
  if (!moneyPattern.test(value)) return "Enter an amount with up to 2 decimal places.";
  if (Number(value) < (allowZero ? 0 : Number.EPSILON)) return allowZero ? "Amount cannot be negative." : "Amount must be greater than zero.";
  return undefined;
}
function serverError(reason: unknown): { message: string; fields: FieldErrors } {
  if (reason instanceof ApiRequestError) return { message: reason.message, fields: reason.details };
  return { message: reason instanceof Error ? reason.message : "The change could not be saved.", fields: {} };
}
function input(e: FormEvent<HTMLFormElement>, validate: () => FieldErrors, save: () => void, setErrors: (errors: FieldErrors) => void, setNotice: (message: string) => void) {
  e.preventDefault();
  setNotice("");
  const errors = validate();
  setErrors(errors);
  if (!Object.keys(errors).length) save();
}
function fieldError(errors: FieldErrors, name: string) { return errors[name]; }

function CatalogPage() {
  const [tab, setTab] = useState<Tab>("products");
  const [page, setPage] = useState(1);
  const [notice, setNotice] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const queryClient = useQueryClient();
  const refresh = async () => { await queryClient.invalidateQueries({ queryKey: ["catalog"] }); };
  const onError = (reason: unknown) => { const parsed = serverError(reason); setNotice(parsed.message); setFieldErrors(parsed.fields); };
  const onSuccess = async (message: string) => { setNotice(message); setFieldErrors({}); await refresh(); };
  const switchTab = (next: Tab) => { setTab(next); setPage(1); setNotice(""); setFieldErrors({}); };

  const products = useQuery({ queryKey: ["catalog", "products", page], queryFn: () => apiRequest<Page<Product>>(`/products?page=${page}&page_size=${pageSize}`), enabled: tab === "products" });
  const plans = useQuery({ queryKey: ["catalog", "plans", page], queryFn: () => apiRequest<Page<Plan>>(`/plans?page=${page}&page_size=${pageSize}`), enabled: tab === "plans" });
  const taxes = useQuery({ queryKey: ["catalog", "taxes", page], queryFn: () => apiRequest<Page<Tax>>(`/taxes?page=${page}&page_size=${pageSize}`), enabled: tab === "taxes" });
  const methods = useQuery({ queryKey: ["catalog", "payment-methods", page], queryFn: () => apiRequest<Page<PaymentMethod>>(`/payment-methods?page=${page}&page_size=${pageSize}`), enabled: tab === "payments" });
  const discounts = useQuery({ queryKey: ["catalog", "discounts", page], queryFn: () => apiRequest<Page<Discount>>(`/discounts?page=${page}&page_size=${pageSize}`), enabled: tab === "discounts" });
  const templates = useQuery({ queryKey: ["catalog", "templates", page], queryFn: () => apiRequest<Page<Template>>(`/quotation-templates?page=${page}&page_size=${pageSize}`), enabled: tab === "templates" });
  const options = useQuery({
    queryKey: ["catalog", "form-options"],
    queryFn: async () => {
      const [productPage, planPage, taxPage] = await Promise.all([
        apiRequest<Page<Product>>("/products?page=1&page_size=100"), apiRequest<Page<Plan>>("/plans?page=1&page_size=100"), apiRequest<Page<Tax>>("/taxes?page=1&page_size=100"),
      ]);
      return { products: productPage.items.filter((item) => item.is_active), plans: planPage.items.filter((item) => item.is_active), taxes: taxPage.items.filter((item) => item.is_active) };
    },
  });
  const variantProductId = Number(options.data?.products[0]?.id ?? 0);
  const [selectedVariantProduct, setSelectedVariantProduct] = useState(0);
  const activeVariantProduct = selectedVariantProduct || variantProductId;
  const variantList = useQuery({ queryKey: ["catalog", "variants", activeVariantProduct], queryFn: () => apiRequest<VariantAttribute[]>(`/products/${activeVariantProduct}/variants`), enabled: activeVariantProduct > 0 });

  const [productName, setProductName] = useState(""); const [productType, setProductType] = useState<Product["type"]>("software"); const [productPrice, setProductPrice] = useState(""); const [costPrice, setCostPrice] = useState("0.00"); const [defaultTaxId, setDefaultTaxId] = useState("");
  const [variantName, setVariantName] = useState("Brand"); const [variantValues, setVariantValues] = useState([{ value: "", extra_price: "" }]);
  const [planName, setPlanName] = useState(""); const [planPrice, setPlanPrice] = useState(""); const [billingPeriod, setBillingPeriod] = useState<Plan["billing_period"]>("monthly"); const [minQuantity, setMinQuantity] = useState("1"); const [availableFrom, setAvailableFrom] = useState(""); const [availableTo, setAvailableTo] = useState(""); const [planFlags, setPlanFlags] = useState({ auto_close: false, closable: true, pausable: true, renewable: true });
  const [taxName, setTaxName] = useState(""); const [taxRate, setTaxRate] = useState(""); const [methodName, setMethodName] = useState("");
  const [discountName, setDiscountName] = useState(""); const [discountType, setDiscountType] = useState<Discount["type"]>("percent"); const [discountValue, setDiscountValue] = useState(""); const [discountScope, setDiscountScope] = useState<Discount["scope"]>("product"); const [minPurchase, setMinPurchase] = useState("0.00"); const [discountMinQuantity, setDiscountMinQuantity] = useState("1"); const [discountStartDate, setDiscountStartDate] = useState(""); const [discountEndDate, setDiscountEndDate] = useState(""); const [maxUses, setMaxUses] = useState(""); const [discountProductIds, setDiscountProductIds] = useState<number[]>([]);
  const [templateName, setTemplateName] = useState(""); const [templatePlanId, setTemplatePlanId] = useState(""); const [validityDays, setValidityDays] = useState("30"); const [templateLines, setTemplateLines] = useState([{ product_id: "", quantity: "1" }]);

  const createProduct = useMutation({ mutationFn: () => apiRequest<Product>("/products", { method: "POST", body: JSON.stringify({ name: productName.trim(), type: productType, sales_price: productPrice, cost_price: costPrice, default_tax_id: defaultTaxId ? Number(defaultTaxId) : null }) }), onSuccess: () => { setProductName(""); setProductPrice(""); void onSuccess("Product created."); }, onError });
  const createVariant = useMutation({ mutationFn: () => apiRequest<VariantAttribute>(`/products/${activeVariantProduct}/variants`, { method: "POST", body: JSON.stringify({ name: variantName.trim(), values: variantValues.map((item) => ({ value: item.value.trim(), extra_price: item.extra_price })) }) }), onSuccess: () => { setVariantValues([{ value: "", extra_price: "" }]); void onSuccess("Variant attribute created."); }, onError });
  const createPlan = useMutation({ mutationFn: () => apiRequest<Plan>("/plans", { method: "POST", body: JSON.stringify({ name: planName.trim(), price: planPrice, billing_period: billingPeriod, min_quantity: Number(minQuantity), available_from: availableFrom || null, available_to: availableTo || null, ...planFlags }) }), onSuccess: () => { setPlanName(""); setPlanPrice(""); void onSuccess("Plan created."); }, onError });
  const createTax = useMutation({ mutationFn: () => apiRequest<Tax>("/taxes", { method: "POST", body: JSON.stringify({ name: taxName.trim(), rate_pct: taxRate }) }), onSuccess: () => { setTaxName(""); setTaxRate(""); void onSuccess("Tax rate created."); }, onError });
  const createMethod = useMutation({ mutationFn: () => apiRequest<PaymentMethod>("/payment-methods", { method: "POST", body: JSON.stringify({ name: methodName.trim() }) }), onSuccess: () => { setMethodName(""); void onSuccess("Payment method created."); }, onError });
  const createDiscount = useMutation({ mutationFn: () => apiRequest<Discount>("/discounts", { method: "POST", body: JSON.stringify({ name: discountName.trim(), type: discountType, value: discountValue, scope: discountScope, min_purchase: minPurchase, min_quantity: Number(discountMinQuantity), start_date: discountStartDate || null, end_date: discountEndDate || null, max_uses: maxUses ? Number(maxUses) : null, product_ids: discountScope === "product" ? discountProductIds : [] }) }), onSuccess: () => { setDiscountName(""); setDiscountValue(""); setDiscountProductIds([]); void onSuccess("Discount created."); }, onError });
  const createTemplate = useMutation({ mutationFn: () => apiRequest<Template>("/quotation-templates", { method: "POST", body: JSON.stringify({ name: templateName.trim(), plan_id: Number(templatePlanId), validity_days: Number(validityDays), lines: templateLines.map((line) => ({ product_id: Number(line.product_id), quantity: Number(line.quantity), variant_value_ids: [] })) }) }), onSuccess: () => { setTemplateName(""); setTemplateLines([{ product_id: "", quantity: "1" }]); void onSuccess("Quotation template created."); }, onError });
  const deactivate = useMutation({ mutationFn: (path: string) => apiRequest<void>(path, { method: "DELETE" }), onSuccess: () => void onSuccess("Record deactivated."), onError });
  const deleteTemplate = useMutation({ mutationFn: (id: number) => apiRequest<void>(`/quotation-templates/${id}`, { method: "DELETE" }), onSuccess: () => void onSuccess("Quotation template deleted."), onError });

  const productColumns: Column<Product>[] = [{ key: "name", header: "Product", render: (row) => <span className="font-semibold">{row.name}</span> }, { key: "type", header: "Type", render: (row) => <span className="capitalize">{row.type}</span> }, { key: "price", header: "Sales price", render: (row) => <Money amount={row.sales_price} /> }, { key: "tax", header: "Default tax", render: (row) => options.data?.taxes.find((tax) => tax.id === row.default_tax_id)?.name ?? "—" }, { key: "active", header: "Status", render: (row) => <StatusChip status={row.is_active ? "active" : "inactive"} /> }, { key: "action", header: "", render: (row) => row.is_active ? <button className="text-sm text-rose-700" onClick={() => window.confirm(`Deactivate ${row.name}?`) && deactivate.mutate(`/products/${row.id}`)}>Deactivate</button> : null }];
  const planColumns: Column<Plan>[] = [{ key: "name", header: "Plan", render: (row) => <span className="font-semibold">{row.name}</span> }, { key: "price", header: "Price", render: (row) => <Money amount={row.price} /> }, { key: "billing", header: "Billing", render: (row) => <span className="capitalize">{row.billing_period}</span> }, { key: "quantity", header: "Min qty", render: (row) => row.min_quantity }, { key: "dates", header: "Availability", render: (row) => `${row.available_from ?? "Any"} – ${row.available_to ?? "Any"}` }, { key: "flags", header: "Flags", render: (row) => [row.auto_close && "Auto close", row.closable && "Closable", row.pausable && "Pausable", row.renewable && "Renewable"].filter(Boolean).join(", ") || "None" }, { key: "action", header: "", render: (row) => row.is_active ? <button className="text-sm text-rose-700" onClick={() => window.confirm(`Deactivate ${row.name}?`) && deactivate.mutate(`/plans/${row.id}`)}>Deactivate</button> : null }];
  const taxColumns: Column<Tax>[] = [{ key: "name", header: "Tax", render: (row) => <span className="font-semibold">{row.name}</span> }, { key: "rate", header: "Rate", render: (row) => `${row.rate_pct}%` }, { key: "status", header: "Status", render: (row) => <StatusChip status={row.is_active ? "active" : "inactive"} /> }, { key: "action", header: "", render: (row) => row.is_active ? <button className="text-sm text-rose-700" onClick={() => window.confirm(`Deactivate ${row.name}?`) && deactivate.mutate(`/taxes/${row.id}`)}>Deactivate</button> : null }];
  const methodColumns: Column<PaymentMethod>[] = [{ key: "name", header: "Payment method", render: (row) => <span className="font-semibold capitalize">{row.name.replaceAll("_", " ")}</span> }, { key: "status", header: "Status", render: (row) => <StatusChip status={row.is_active ? "active" : "inactive"} /> }, { key: "action", header: "", render: (row) => row.is_active ? <button className="text-sm text-rose-700" onClick={() => window.confirm(`Deactivate ${row.name}?`) && deactivate.mutate(`/payment-methods/${row.id}`)}>Deactivate</button> : null }];
  const discountColumns: Column<Discount>[] = [{ key: "name", header: "Discount", render: (row) => <span className="font-semibold">{row.name}</span> }, { key: "value", header: "Value", render: (row) => row.type === "percent" ? `${row.value}%` : <Money amount={row.value} /> }, { key: "scope", header: "Scope", render: (row) => row.scope === "subscription" ? "Subscription" : `Products: ${row.product_ids.map((id) => options.data?.products.find((product) => product.id === id)?.name ?? id).join(", ")}` }, { key: "requirements", header: "Minimum", render: (row) => `${row.min_quantity} qty · ${row.min_purchase}` }, { key: "dates", header: "Dates", render: (row) => `${row.start_date ?? "Any"} – ${row.end_date ?? "Any"}` }, { key: "uses", header: "Uses", render: (row) => `${row.uses_count}${row.max_uses ? ` / ${row.max_uses}` : ""}` }, { key: "action", header: "", render: (row) => row.is_active ? <button className="text-sm text-rose-700" onClick={() => window.confirm(`Deactivate ${row.name}?`) && deactivate.mutate(`/discounts/${row.id}`)}>Deactivate</button> : null }];
  const templateColumns: Column<Template>[] = [{ key: "name", header: "Template", render: (row) => <span className="font-semibold">{row.name}</span> }, { key: "plan", header: "Plan", render: (row) => options.data?.plans.find((plan) => plan.id === row.plan_id)?.name ?? row.plan_id }, { key: "lines", header: "Lines", render: (row) => row.lines.map((line) => `${options.data?.products.find((product) => product.id === line.product_id)?.name ?? line.product_id} × ${line.quantity}`).join(", ") }, { key: "validity", header: "Validity", render: (row) => `${row.validity_days} days` }, { key: "action", header: "", render: (row) => <button className="text-sm text-rose-700" onClick={() => window.confirm(`Delete ${row.name}?`) && deleteTemplate.mutate(row.id)}>Delete</button> }];

  function showList<T>(query: { isLoading: boolean; error: unknown; data?: Page<T> }, columns: Column<T>[]) {
    if (query.isLoading) return <LoadingState label="Loading catalog…" />;
    if (query.error || !query.data) return <ErrorState message="Could not load this catalog section." onRetry={() => void queryClient.invalidateQueries({ queryKey: ["catalog", tab] })} />;
    return <DataTable rows={query.data.items} columns={columns} rowKey={(row) => (row as { id: number }).id} page={query.data.page} pageSize={query.data.page_size} total={query.data.total} onPageChange={setPage} />;
  }

  const validateProduct = () => {
    const errors: FieldErrors = {};
    const name = nameError(productName, 160, "Name"); if (name) errors.name = name;
    const price = amountError(productPrice); if (price) errors.sales_price = price;
    const cost = amountError(costPrice); if (cost) errors.cost_price = cost;
    return errors;
  };
  const validateVariant = () => {
    const errors: FieldErrors = {};
    const name = nameError(variantName, 100, "Attribute name"); if (name) errors.name = name;
    if (!variantValues.length || variantValues.length > 50) errors.values = "Add between 1 and 50 values.";
    const seenValues = new Set<string>();
    variantValues.forEach((item, index) => {
      const value = nameError(item.value, 100, "Value"); if (value) errors[`values.${index}.value`] = value;
      const extra = amountError(item.extra_price); if (extra) errors[`values.${index}.extra_price`] = extra;
      const normalized = item.value.trim();
      if (normalized && seenValues.has(normalized)) errors[`values.${index}.value`] = "Variant values must be unique within an attribute.";
      seenValues.add(normalized);
    });
    if (!activeVariantProduct) errors.product_id = "Choose a product.";
    return errors;
  };
  const validatePlan = () => {
    const errors: FieldErrors = {};
    const name = nameError(planName, 160, "Plan name"); if (name) errors.name = name;
    const price = amountError(planPrice); if (price) errors.price = price;
    if (!/^\d+$/.test(minQuantity) || Number(minQuantity) < 1) errors.min_quantity = "Minimum quantity must be a whole number of at least 1.";
    if (availableFrom && availableTo && availableTo < availableFrom) errors.available_to = "End date must be on or after start date.";
    return errors;
  };
  const validateTax = () => {
    const errors: FieldErrors = {};
    const name = nameError(taxName, 100, "Tax name"); if (name) errors.name = name;
    const rate = amountError(taxRate); if (rate) errors.rate_pct = rate;
    else if (Number(taxRate) > 100) errors.rate_pct = "Rate cannot exceed 100%.";
    return errors;
  };
  const validateMethod = (): FieldErrors => { const name = nameError(methodName, 40, "Payment method"); return name ? { name } : {}; };
  const validateDiscount = () => {
    const errors: FieldErrors = {};
    const name = nameError(discountName, 160, "Discount name"); if (name) errors.name = name;
    const value = amountError(discountValue, false); if (value) errors.value = value;
    else if (discountType === "percent" && Number(discountValue) > 100) errors.value = "Percentage cannot exceed 100.";
    const purchase = amountError(minPurchase); if (purchase) errors.min_purchase = purchase;
    if (!/^\d+$/.test(discountMinQuantity) || Number(discountMinQuantity) < 1) errors.min_quantity = "Minimum quantity must be a whole number of at least 1.";
    if (discountStartDate && discountEndDate && discountEndDate < discountStartDate) errors.end_date = "End date must be on or after start date.";
    if (maxUses && (!/^\d+$/.test(maxUses) || Number(maxUses) < 1)) errors.max_uses = "Maximum uses must be a whole number of at least 1.";
    if (discountScope === "product" && !discountProductIds.length) errors.product_ids = "Choose at least one product for a product discount.";
    if (discountScope === "product" && discountProductIds.length > 100) errors.product_ids = "Choose no more than 100 products.";
    return errors;
  };
  const validateTemplate = () => {
    const errors: FieldErrors = {};
    const name = nameError(templateName, 160, "Template name"); if (name) errors.name = name;
    if (!templatePlanId) errors.plan_id = "Choose a plan.";
    if (!/^\d+$/.test(validityDays) || Number(validityDays) < 1 || Number(validityDays) > 365) errors.validity_days = "Validity must be a whole number from 1 to 365.";
    if (!templateLines.length || templateLines.length > 100) errors.lines = "Add between 1 and 100 product lines.";
    templateLines.forEach((line, index) => {
      if (!line.product_id) errors[`lines.${index}.product_id`] = "Choose a product.";
      if (!/^\d+$/.test(line.quantity) || Number(line.quantity) < 1 || Number(line.quantity) > 100000) errors[`lines.${index}.quantity`] = "Quantity must be a whole number from 1 to 100000.";
    });
    return errors;
  };

  const listQuery = tab === "products" ? products : tab === "plans" ? plans : tab === "taxes" ? taxes : tab === "payments" ? methods : tab === "discounts" ? discounts : templates;
  const list = tab === "products" ? showList(products, productColumns) : tab === "plans" ? showList(plans, planColumns) : tab === "taxes" ? showList(taxes, taxColumns) : tab === "payments" ? showList(methods, methodColumns) : tab === "discounts" ? showList(discounts, discountColumns) : tab === "templates" ? showList(templates, templateColumns) : null;

  return <Screen eyebrow="Admin" title="Catalog settings" description="Manage products, variants, plans, taxes, payment methods, discounts, and quotation templates.">
    <div role="tablist" aria-label="Catalog settings" className="flex flex-wrap gap-2 rounded-xl border border-slate-200 bg-white p-2">{tabs.map((item) => <button key={item.id} role="tab" aria-selected={tab === item.id} onClick={() => switchTab(item.id)} className={`rounded-lg px-3 py-2 text-sm font-semibold ${tab === item.id ? "bg-indigo-600 text-white" : "text-slate-600 hover:bg-slate-100"}`}>{item.label}</button>)}</div>
    {notice && <p role="status" className="rounded-lg border border-indigo-100 bg-indigo-50 px-4 py-3 text-sm text-indigo-900">{notice}</p>}
    {options.isError && <ErrorState message="Form choices could not be loaded. Retry before adding catalog settings." onRetry={() => void options.refetch()} />}

    {tab === "products" && <>
      <section className="rounded-xl border border-slate-200 bg-white p-5"><h2 className="font-semibold">Add product</h2><form className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4" onSubmit={(e) => input(e, validateProduct, () => createProduct.mutate(), setFieldErrors, setNotice)}>
        <FormField label="Name" name="name" value={productName} maxLength={160} error={fieldError(fieldErrors, "name")} onChange={(e) => setProductName(e.target.value)} required />
        <label className={labelClass}>Type<select className={controlClass} value={productType} onChange={(e) => setProductType(e.target.value as Product["type"])}>{["software", "service", "addon", "physical"].map((value) => <option key={value}>{value}</option>)}</select></label>
        <FormField label="Sales price" name="sales_price" type="number" min="0" step="0.01" value={productPrice} error={fieldError(fieldErrors, "sales_price")} onChange={(e) => setProductPrice(e.target.value)} required />
        <FormField label="Cost price" name="cost_price" type="number" min="0" step="0.01" value={costPrice} error={fieldError(fieldErrors, "cost_price")} onChange={(e) => setCostPrice(e.target.value)} required />
        <label className={labelClass}>Default tax<select className={controlClass} value={defaultTaxId} onChange={(e) => setDefaultTaxId(e.target.value)}><option value="">No default tax</option>{options.data?.taxes.map((tax) => <option key={tax.id} value={tax.id}>{tax.name} ({tax.rate_pct}%)</option>)}</select></label>
        <button className={`${primaryButton} self-end`} disabled={createProduct.isPending}>Add product</button></form></section>
      {list}
    </>}

    {tab === "variants" && <>
      <section className="rounded-xl border border-slate-200 bg-white p-5"><h2 className="font-semibold">Add product variant</h2><p className="mt-1 text-sm text-slate-500">Create an attribute and value with its extra unit price, such as Brand → Odoo → +560.</p><form className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4" onSubmit={(e) => input(e, validateVariant, () => createVariant.mutate(), setFieldErrors, setNotice)}>
        <label className={labelClass}>Product<select className={controlClass} value={activeVariantProduct || ""} onChange={(e) => setSelectedVariantProduct(Number(e.target.value))}><option value="">Choose product</option>{options.data?.products.map((product) => <option key={product.id} value={product.id}>{product.name}</option>)}</select>{fieldError(fieldErrors, "product_id") && <span className="mt-1 block text-xs text-rose-600">{fieldErrors.product_id}</span>}</label>
        <FormField label="Attribute" name="name" value={variantName} maxLength={100} error={fieldError(fieldErrors, "name")} onChange={(e) => setVariantName(e.target.value)} required />
        <fieldset className="space-y-3 rounded-lg border border-slate-200 p-3 sm:col-span-2 xl:col-span-4"><legend className="px-1 text-sm font-medium">Values and extra prices</legend>{variantValues.map((item, index) => <div key={index} className="grid gap-3 sm:grid-cols-[1fr_1fr_auto]"><FormField label="Value" name={`values.${index}.value`} value={item.value} maxLength={100} error={fieldError(fieldErrors, `values.${index}.value`)} onChange={(e) => setVariantValues((current) => current.map((row, i) => i === index ? { ...row, value: e.target.value } : row))} required /><FormField label="Extra price" name={`values.${index}.extra_price`} type="number" min="0" step="0.01" value={item.extra_price} error={fieldError(fieldErrors, `values.${index}.extra_price`)} onChange={(e) => setVariantValues((current) => current.map((row, i) => i === index ? { ...row, extra_price: e.target.value } : row))} required /><button type="button" className={`${secondaryButton} self-end`} disabled={variantValues.length === 1} onClick={() => setVariantValues((current) => current.filter((_, i) => i !== index))}>Remove</button></div>)}{fieldError(fieldErrors, "values") && <p className="text-xs text-rose-600">{fieldErrors.values}</p>}<button type="button" className={secondaryButton} disabled={variantValues.length >= 50} onClick={() => setVariantValues((current) => [...current, { value: "", extra_price: "" }])}>Add another value</button></fieldset>
        <button className={`${primaryButton} self-end`} disabled={createVariant.isPending || !activeVariantProduct}>Add variant attribute</button></form></section>
      <section className="space-y-3"><h2 className="font-semibold">Existing variants</h2>{variantList.isLoading ? <LoadingState /> : variantList.error ? <ErrorState message="Could not load this product's variants." onRetry={() => void variantList.refetch()} /> : <div className="space-y-3">{variantList.data?.length ? variantList.data.map((attribute) => <article key={attribute.id} className="rounded-xl border border-slate-200 bg-white p-4"><h3 className="font-semibold">{attribute.name}</h3><ul className="mt-2 flex flex-wrap gap-2">{attribute.values.map((value) => <li key={value.id} className="rounded-full bg-slate-100 px-3 py-1 text-sm">{value.value} · +<Money amount={value.extra_price} /></li>)}</ul></article>) : <p className="rounded-xl border border-slate-200 bg-white p-5 text-sm text-slate-500">No variants for the selected product yet.</p>}</div>}</section>
    </>}

    {tab === "plans" && <>
      <section className="rounded-xl border border-slate-200 bg-white p-5"><h2 className="font-semibold">Add plan</h2><form className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4" onSubmit={(e) => input(e, validatePlan, () => createPlan.mutate(), setFieldErrors, setNotice)}>
        <FormField label="Plan name" name="name" value={planName} maxLength={160} error={fieldError(fieldErrors, "name")} onChange={(e) => setPlanName(e.target.value)} required />
        <FormField label="Price" name="price" type="number" min="0" step="0.01" value={planPrice} error={fieldError(fieldErrors, "price")} onChange={(e) => setPlanPrice(e.target.value)} required />
        <label className={labelClass}>Billing period<select className={controlClass} value={billingPeriod} onChange={(e) => setBillingPeriod(e.target.value as Plan["billing_period"])}>{["daily", "weekly", "monthly", "yearly"].map((value) => <option key={value}>{value}</option>)}</select></label>
        <FormField label="Minimum quantity" name="min_quantity" type="number" min="1" step="1" value={minQuantity} error={fieldError(fieldErrors, "min_quantity")} onChange={(e) => setMinQuantity(e.target.value)} required />
        <FormField label="Available from" name="available_from" type="date" value={availableFrom} error={fieldError(fieldErrors, "available_from")} onChange={(e) => setAvailableFrom(e.target.value)} />
        <FormField label="Available to" name="available_to" type="date" value={availableTo} error={fieldError(fieldErrors, "available_to")} onChange={(e) => setAvailableTo(e.target.value)} />
        <div className="grid gap-2 sm:grid-cols-2 xl:col-span-2">{(["auto_close", "closable", "pausable", "renewable"] as const).map((flag) => <label key={flag} className="flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" checked={planFlags[flag]} onChange={(e) => setPlanFlags((current) => ({ ...current, [flag]: e.target.checked }))} />{flag.replace("_", " ")}</label>)}</div>
        <button className={`${primaryButton} self-end`} disabled={createPlan.isPending}>Add plan</button></form></section>
      {list}
    </>}

    {tab === "taxes" && <>
      <section className="rounded-xl border border-slate-200 bg-white p-5"><h2 className="font-semibold">Add tax rate</h2><form className="mt-4 grid gap-4 sm:grid-cols-3" onSubmit={(e) => input(e, validateTax, () => createTax.mutate(), setFieldErrors, setNotice)}>
        <FormField label="Tax name" name="name" value={taxName} maxLength={100} error={fieldError(fieldErrors, "name")} onChange={(e) => setTaxName(e.target.value)} required />
        <FormField label="Rate (%)" name="rate_pct" type="number" min="0" max="100" step="0.01" value={taxRate} error={fieldError(fieldErrors, "rate_pct")} onChange={(e) => setTaxRate(e.target.value)} required />
        <button className={`${primaryButton} self-end`} disabled={createTax.isPending}>Add tax rate</button></form></section>
      {list}
    </>}

    {tab === "payments" && <>
      <section className="rounded-xl border border-slate-200 bg-white p-5"><h2 className="font-semibold">Add payment method</h2><form className="mt-4 grid gap-4 sm:grid-cols-2" onSubmit={(e) => input(e, validateMethod, () => createMethod.mutate(), setFieldErrors, setNotice)}>
        <FormField label="Name" name="name" value={methodName} maxLength={40} hint="Saved lowercase, for example bank_transfer or upi." error={fieldError(fieldErrors, "name")} onChange={(e) => setMethodName(e.target.value)} required />
        <button className={`${primaryButton} self-end`} disabled={createMethod.isPending}>Add payment method</button></form></section>
      {list}
    </>}

    {tab === "discounts" && <>
      <section className="rounded-xl border border-slate-200 bg-white p-5"><h2 className="font-semibold">Add discount</h2><form className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4" onSubmit={(e) => input(e, validateDiscount, () => createDiscount.mutate(), setFieldErrors, setNotice)}>
        <FormField label="Name" name="name" value={discountName} maxLength={160} error={fieldError(fieldErrors, "name")} onChange={(e) => setDiscountName(e.target.value)} required />
        <label className={labelClass}>Type<select className={controlClass} value={discountType} onChange={(e) => setDiscountType(e.target.value as Discount["type"])}><option value="percent">Percent</option><option value="fixed">Fixed amount</option></select></label>
        <FormField label={discountType === "percent" ? "Percent off" : "Amount off"} name="value" type="number" min="0.01" max={discountType === "percent" ? 100 : undefined} step="0.01" value={discountValue} error={fieldError(fieldErrors, "value")} onChange={(e) => setDiscountValue(e.target.value)} required />
        <label className={labelClass}>Scope<select className={controlClass} value={discountScope} onChange={(e) => { setDiscountScope(e.target.value as Discount["scope"]); setDiscountProductIds([]); }}><option value="product">Selected products</option><option value="subscription">Subscription</option></select></label>
        <FormField label="Minimum purchase" name="min_purchase" type="number" min="0" step="0.01" value={minPurchase} error={fieldError(fieldErrors, "min_purchase")} onChange={(e) => setMinPurchase(e.target.value)} required />
        <FormField label="Minimum quantity" name="min_quantity" type="number" min="1" step="1" value={discountMinQuantity} error={fieldError(fieldErrors, "min_quantity")} onChange={(e) => setDiscountMinQuantity(e.target.value)} required />
        <FormField label="Starts on" name="start_date" type="date" value={discountStartDate} error={fieldError(fieldErrors, "start_date")} onChange={(e) => setDiscountStartDate(e.target.value)} />
        <FormField label="Ends on" name="end_date" type="date" value={discountEndDate} error={fieldError(fieldErrors, "end_date")} onChange={(e) => setDiscountEndDate(e.target.value)} />
        <FormField label="Maximum uses" name="max_uses" type="number" min="1" step="1" value={maxUses} hint="Leave blank for unlimited uses." error={fieldError(fieldErrors, "max_uses")} onChange={(e) => setMaxUses(e.target.value)} />
        {discountScope === "product" && <fieldset className="rounded-lg border border-slate-200 p-3 sm:col-span-2 xl:col-span-4"><legend className="px-1 text-sm font-medium">Applies to products</legend><div className="flex flex-wrap gap-x-5 gap-y-2">{options.data?.products.map((product) => <label key={product.id} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={discountProductIds.includes(product.id)} onChange={(e) => setDiscountProductIds((current) => e.target.checked ? [...current, product.id] : current.filter((id) => id !== product.id))} />{product.name}</label>)}</div>{fieldError(fieldErrors, "product_ids") && <p className="mt-2 text-xs text-rose-600">{fieldErrors.product_ids}</p>}</fieldset>}
        <button className={`${primaryButton} self-end`} disabled={createDiscount.isPending}>Add discount</button></form></section>
      {list}
    </>}

    {tab === "templates" && <>
      <section className="rounded-xl border border-slate-200 bg-white p-5"><h2 className="font-semibold">Add quotation template</h2><form className="mt-4 space-y-4" onSubmit={(e) => input(e, validateTemplate, () => createTemplate.mutate(), setFieldErrors, setNotice)}>
        <div className="grid gap-4 sm:grid-cols-3"><FormField label="Template name" name="name" value={templateName} maxLength={160} error={fieldError(fieldErrors, "name")} onChange={(e) => setTemplateName(e.target.value)} required />
          <label className={labelClass}>Plan<select className={controlClass} value={templatePlanId} onChange={(e) => setTemplatePlanId(e.target.value)}><option value="">Choose plan</option>{options.data?.plans.map((plan) => <option key={plan.id} value={plan.id}>{plan.name}</option>)}</select>{fieldError(fieldErrors, "plan_id") && <span className="mt-1 block text-xs text-rose-600">{fieldErrors.plan_id}</span>}</label>
          <FormField label="Validity days" name="validity_days" type="number" min="1" max="365" step="1" value={validityDays} error={fieldError(fieldErrors, "validity_days")} onChange={(e) => setValidityDays(e.target.value)} required /></div>
        <fieldset className="space-y-3 rounded-lg border border-slate-200 p-4"><legend className="px-1 text-sm font-semibold">Product lines</legend>{templateLines.map((line, index) => <div key={index} className="grid gap-3 sm:grid-cols-[1fr_180px_auto]"><label className={labelClass}>Product<select className={controlClass} value={line.product_id} onChange={(e) => setTemplateLines((current) => current.map((row, i) => i === index ? { ...row, product_id: e.target.value } : row))}><option value="">Choose product</option>{options.data?.products.map((product) => <option key={product.id} value={product.id}>{product.name}</option>)}</select>{fieldError(fieldErrors, `lines.${index}.product_id`) && <span className="mt-1 block text-xs text-rose-600">{fieldErrors[`lines.${index}.product_id`]}</span>}</label><FormField label="Quantity" name={`lines.${index}.quantity`} type="number" min="1" max="100000" step="1" value={line.quantity} error={fieldError(fieldErrors, `lines.${index}.quantity`)} onChange={(e) => setTemplateLines((current) => current.map((row, i) => i === index ? { ...row, quantity: e.target.value } : row))} required /><button type="button" className={`${secondaryButton} self-end`} disabled={templateLines.length === 1} onClick={() => setTemplateLines((current) => current.filter((_, i) => i !== index))}>Remove</button></div>)}{fieldError(fieldErrors, "lines") && <p className="text-xs text-rose-600">{fieldErrors.lines}</p>}<button type="button" className={secondaryButton} disabled={templateLines.length >= 100} onClick={() => setTemplateLines((current) => [...current, { product_id: "", quantity: "1" }])}>Add another line</button></fieldset>
        <button className={primaryButton} disabled={createTemplate.isPending}>Add quotation template</button></form></section>
      {list}
    </>}
    {listQuery.error && <p className="sr-only" role="alert">Catalog list failed to load.</p>}
  </Screen>;
}

export const routes = [{ path: "catalog", element: <RoleGuard roles={["admin"]}><CatalogPage /></RoleGuard> }];
