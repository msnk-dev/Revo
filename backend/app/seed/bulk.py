"""Load the documented 1k customer / 2k subscription performance fixture."""

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Customer, Invoice, InvoiceLine, Payment, PaymentMethod, Plan, Product, Subscription, SubscriptionLine, Tax


def _chunks(values, size=500):
    for start in range(0, len(values), size):
        yield values[start : start + size]


def seed_bulk() -> None:
    with SessionLocal.begin() as db:
        if db.scalar(select(func.count()).select_from(Customer).where(Customer.email.like("bulk-%@revo.local"))):
            raise RuntimeError("Bulk fixtures already exist; reset the development database before reseeding")

        customers = [Customer(name=f"Bulk Customer {i:04d}", email=f"bulk-{i:04d}@revo.local", is_active=True) for i in range(1000)]
        db.add_all(customers)
        db.flush()
        tax = Tax(name="Bulk GST 18%", rate_pct=Decimal("18.00"), is_active=True)
        product = Product(name="Bulk Service", type="service", sales_price=Decimal("100.00"), cost_price=Decimal("25.00"), is_active=True)
        plan = Plan(name="Bulk Monthly", price=Decimal("100.00"), billing_period="monthly", min_quantity=1, is_active=True)
        method = PaymentMethod(name="bulk_transfer", is_active=True)
        db.add_all([tax, product, plan, method])
        db.flush()
        product.default_tax_id = tax.id

        subscriptions = []
        for index in range(2000):
            subscriptions.append(Subscription(
                number=f"BULK-SUB-{index + 1:06d}", customer_id=customers[index // 2].id,
                plan_id=plan.id, status="active", start_date=date(2025, 1, 1),
                next_invoice_date=date(2027, 1, 1), payment_terms_days=14, is_paused=False,
            ))
        db.add_all(subscriptions)
        db.flush()
        lines = [SubscriptionLine(subscription_id=sub.id, product_id=product.id, description="Bulk Service",
                                  quantity=1, unit_price=Decimal("100.00"), tax_id=tax.id) for sub in subscriptions]
        db.add_all(lines)
        db.flush()

        invoices = []
        for sub_index, sub in enumerate(subscriptions):
            for period in range(10):
                year = 2025 + (period // 12)
                month = (period % 12) + 1
                start = date(year, month, 1)
                end = date(year, month, 28)
                payment_index = sub_index * 10 + period
                is_paid = payment_index < 16000
                invoices.append(Invoice(
                    number=f"BULK-INV-{payment_index + 1:06d}", subscription_id=sub.id,
                    customer_id=sub.customer_id, status="paid" if is_paid else "confirmed",
                    invoice_date=end, due_date=end, period_start=start, period_end=end,
                    subtotal=Decimal("100.00"), discount_total=Decimal("0.00"), tax_total=Decimal("18.00"),
                    total=Decimal("118.00"), amount_paid=Decimal("118.00") if is_paid else Decimal("0.00"),
                    amount_due=Decimal("0.00") if is_paid else Decimal("118.00"),
                ))
        for batch in _chunks(invoices):
            db.add_all(batch)
            db.flush()
        db.flush()
        invoice_ids = list(db.scalars(select(Invoice.id).where(Invoice.number.like("BULK-INV-%")).order_by(Invoice.id).limit(16000)))
        # The fixture has one settled payment on each of its first 16k invoices.
        db.add_all(Payment(invoice_id=invoice_id, method_id=method.id, amount=Decimal("118.00"),
                           paid_on=date(2025, 11, 1)) for invoice_id in invoice_ids)
        db.flush()
        all_invoices = list(db.scalars(select(Invoice).where(Invoice.number.like("BULK-INV-%")).order_by(Invoice.id)))
        db.add_all(InvoiceLine(invoice_id=invoice.id, product_id=product.id, description="Bulk Service",
                               quantity=1, unit_price=Decimal("100.00"), variant_extra=Decimal("0.00"),
                               discount_amount=Decimal("0.00"), tax_name=tax.name, tax_rate_pct=tax.rate_pct,
                               tax_amount=Decimal("18.00"), line_total=Decimal("118.00")) for invoice in all_invoices)

    print("Bulk fixtures loaded: 1,000 customers, 2,000 subscriptions, 20,000 invoices, 16,000 payments")


if __name__ == "__main__":
    seed_bulk()
