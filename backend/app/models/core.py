from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('admin', 'staff', 'customer')", name="ck_users_role"),)

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


Index("uq_users_email_lower", func.lower(User.email), unique=True)


class PasswordResetToken(TimestampMixin, Base):
    __tablename__ = "password_reset_tokens"
    __table_args__ = (UniqueConstraint("token_hash", name="uq_password_reset_token_hash"),)

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Customer(TimestampMixin, Base):
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("user_id", name="uq_customers_user_id"),)

    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(40))
    company: Mapped[str | None] = mapped_column(String(160))
    billing_address: Mapped[str | None] = mapped_column(Text)
    tax_id: Mapped[str | None] = mapped_column(String(80))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Tax(TimestampMixin, Base):
    __tablename__ = "taxes"
    __table_args__ = (CheckConstraint("rate_pct >= 0 AND rate_pct <= 100", name="ck_taxes_rate_pct"),)

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    rate_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Product(TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("type IN ('service', 'software', 'addon', 'physical')", name="ck_products_type"),
        CheckConstraint("sales_price >= 0 AND cost_price >= 0", name="ck_products_nonnegative_prices"),
    )

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    type: Mapped[str] = mapped_column(String(24), nullable=False)
    sales_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cost_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    notes: Mapped[str | None] = mapped_column(Text)
    default_tax_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("taxes.id", ondelete="SET NULL"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ProductVariantAttribute(TimestampMixin, Base):
    __tablename__ = "product_variant_attributes"
    __table_args__ = (UniqueConstraint("product_id", "name", name="uq_variant_attribute_product_name"),)

    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class ProductVariantValue(TimestampMixin, Base):
    __tablename__ = "product_variant_values"
    __table_args__ = (
        UniqueConstraint("attribute_id", "value", name="uq_variant_value_attribute_value"),
        CheckConstraint("extra_price >= 0", name="ck_variant_value_extra_price"),
    )

    attribute_id: Mapped[int] = mapped_column(
        ForeignKey("product_variant_attributes.id", ondelete="CASCADE"), nullable=False
    )
    value: Mapped[str] = mapped_column(String(100), nullable=False)
    extra_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))


class Plan(TimestampMixin, Base):
    __tablename__ = "plans"
    __table_args__ = (
        CheckConstraint("billing_period IN ('daily', 'weekly', 'monthly', 'yearly')", name="ck_plans_billing_period"),
        CheckConstraint("min_quantity >= 1", name="ck_plans_min_quantity"),
        CheckConstraint("available_to IS NULL OR available_from IS NULL OR available_to >= available_from", name="ck_plans_availability"),
        CheckConstraint("price >= 0", name="ck_plans_nonnegative_price"),
    )

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    billing_period: Mapped[str] = mapped_column(String(16), nullable=False)
    min_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    available_from: Mapped[date | None] = mapped_column(Date)
    available_to: Mapped[date | None] = mapped_column(Date)
    auto_close: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    closable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    pausable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    renewable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class QuotationTemplate(TimestampMixin, Base):
    __tablename__ = "quotation_templates"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    plan_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("plans.id"), nullable=False)
    validity_days: Mapped[int] = mapped_column(Integer, nullable=False)


class QuotationTemplateLine(TimestampMixin, Base):
    __tablename__ = "quotation_template_lines"
    __table_args__ = (CheckConstraint("quantity >= 1", name="ck_quotation_template_line_quantity"),)

    template_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("quotation_templates.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)


class QuotationTemplateLineVariant(TimestampMixin, Base):
    __tablename__ = "quotation_template_line_variants"
    __table_args__ = (UniqueConstraint("line_id", "variant_value_id", name="uq_template_line_variant"),)

    line_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("quotation_template_lines.id", ondelete="CASCADE"), nullable=False)
    variant_value_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("product_variant_values.id"), nullable=False)


class Subscription(TimestampMixin, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'quotation', 'confirmed', 'active', 'closed')", name="ck_subscriptions_status"),
        CheckConstraint("expiry_date IS NULL OR expiry_date >= start_date", name="ck_subscriptions_expiry_after_start"),
        Index("ix_subscriptions_next_invoice_active_unpaused", "next_invoice_date", postgresql_where=text("status = 'active' AND is_paused = false")),
    )

    number: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    customer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("customers.id"), nullable=False)
    plan_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("plans.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    next_invoice_date: Mapped[date | None] = mapped_column(Date)
    payment_terms_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quotation_expires_on: Mapped[date | None] = mapped_column(Date)
    is_paused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))


Index("ix_subscriptions_status", Subscription.status)
Index("ix_subscriptions_customer_id", Subscription.customer_id)


class SubscriptionLine(TimestampMixin, Base):
    __tablename__ = "subscription_lines"
    __table_args__ = (CheckConstraint("quantity >= 1", name="ck_subscription_line_quantity"),)

    subscription_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("products.id"), nullable=False)
    description: Mapped[str] = mapped_column(String(240), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tax_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("taxes.id", ondelete="SET NULL"))


class SubscriptionLineVariant(TimestampMixin, Base):
    __tablename__ = "subscription_line_variants"
    __table_args__ = (UniqueConstraint("line_id", "variant_value_id", name="uq_subscription_line_variant"),)

    line_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("subscription_lines.id", ondelete="CASCADE"), nullable=False)
    variant_value_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("product_variant_values.id"), nullable=False)


class SubscriptionStatusHistory(TimestampMixin, Base):
    __tablename__ = "subscription_status_history"

    subscription_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(16))
    to_status: Mapped[str] = mapped_column(String(16), nullable=False)
    changed_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Discount(TimestampMixin, Base):
    __tablename__ = "discounts"
    __table_args__ = (
        CheckConstraint("type IN ('fixed', 'percent')", name="ck_discounts_type"),
        CheckConstraint("scope IN ('product', 'subscription')", name="ck_discounts_scope"),
        CheckConstraint("value > 0", name="ck_discounts_value_positive"),
        CheckConstraint("type != 'percent' OR value <= 100", name="ck_discounts_percent_max"),
        CheckConstraint("end_date IS NULL OR start_date IS NULL OR end_date >= start_date", name="ck_discounts_dates"),
        CheckConstraint("min_quantity >= 1", name="ck_discounts_min_quantity"),
        CheckConstraint("max_uses IS NULL OR max_uses >= 1", name="ck_discounts_max_uses"),
    )

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    scope: Mapped[str] = mapped_column(String(20), nullable=False)
    min_purchase: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    min_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    max_uses: Mapped[int | None] = mapped_column(Integer)
    uses_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class DiscountProduct(TimestampMixin, Base):
    __tablename__ = "discount_products"
    __table_args__ = (UniqueConstraint("discount_id", "product_id", name="uq_discount_product"),)

    discount_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("discounts.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)


class Invoice(TimestampMixin, Base):
    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'confirmed', 'paid', 'cancelled')", name="ck_invoices_status"),
        UniqueConstraint("subscription_id", "period_start", name="uq_invoice_subscription_period_start"),
        Index("ix_invoices_status_due_date", "status", "due_date"),
    )

    number: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    subscription_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("subscriptions.id"), nullable=False)
    customer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("customers.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tax_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    amount_due: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


Index("ix_invoices_customer_status", Invoice.customer_id, Invoice.status)
Index("ix_invoices_invoice_date", Invoice.invoice_date)


class InvoiceLine(TimestampMixin, Base):
    __tablename__ = "invoice_lines"

    invoice_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("products.id"), nullable=False)
    description: Mapped[str] = mapped_column(String(240), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("discounts.id", ondelete="SET NULL"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tax_name: Mapped[str | None] = mapped_column(String(100))
    tax_rate_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)


class PaymentMethod(TimestampMixin, Base):
    __tablename__ = "payment_methods"

    name: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_payments_amount_positive"),)

    invoice_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("invoices.id"), nullable=False)
    method_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("payment_methods.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    paid_on: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[str | None] = mapped_column(String(500))
    recorded_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))


Index("ix_payments_invoice_id", Payment.invoice_id)
Index("ix_payments_paid_on", Payment.paid_on)

