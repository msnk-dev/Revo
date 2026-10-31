from datetime import date
from decimal import Decimal
import os
import secrets

from argon2 import PasswordHasher
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import (
    Customer,
    PaymentMethod,
    Plan,
    Product,
    ProductVariantAttribute,
    ProductVariantValue,
    Subscription,
    SubscriptionLine,
    SubscriptionLineVariant,
    SubscriptionStatusHistory,
    Tax,
    User,
    QuotationTemplate,
    QuotationTemplateLine,
    QuotationTemplateLineVariant,
)

ADMIN_EMAIL = "admin@revo.local"
ADMIN_PASSWORD = os.environ.get("REVO_DEMO_ADMIN_PASSWORD") or f"{secrets.token_urlsafe(18)}A!"
CUSTOMER_PASSWORD = os.environ.get("REVO_DEMO_CUSTOMER_PASSWORD") or f"{secrets.token_urlsafe(18)}B!"


def seed_demo_data() -> None:
    hasher = PasswordHasher()
    with SessionLocal.begin() as db:
        existing = db.scalar(select(User).where(func.lower(User.email) == ADMIN_EMAIL))
        if existing:
            print(f"Demo data already exists. Admin login: {ADMIN_EMAIL}; the original password is unchanged.")
            return

        admin = User(email=ADMIN_EMAIL, password_hash=hasher.hash(ADMIN_PASSWORD), role="admin", is_active=True)
        customer_user = User(
            email="customer@revo.local",
            password_hash=hasher.hash(CUSTOMER_PASSWORD),
            role="customer",
            is_active=True,
        )
        db.add_all([admin, customer_user])
        db.flush()

        customer = Customer(
            user_id=customer_user.id,
            name="Demo Customer",
            email=customer_user.email,
            company="Brightloop Demo",
        )
        tax = Tax(name="GST 18%", rate_pct=Decimal("18.00"), is_active=True)
        db.add_all([customer, tax])
        db.flush()

        product = Product(
            name="Revo Subscription",
            type="software",
            sales_price=Decimal("1200.00"),
            cost_price=Decimal("0.00"),
            default_tax_id=tax.id,
            is_active=True,
        )
        plan = Plan(
            name="Monthly",
            price=Decimal("1200.00"),
            billing_period="monthly",
            min_quantity=1,
            auto_close=False,
            closable=True,
            pausable=True,
            renewable=True,
            is_active=True,
        )
        db.add_all([product, plan])
        db.flush()

        attribute = ProductVariantAttribute(product_id=product.id, name="Brand")
        db.add(attribute)
        db.flush()
        variant = ProductVariantValue(attribute_id=attribute.id, value="Odoo", extra_price=Decimal("560.00"))
        db.add(variant)
        db.flush()

        subscription = Subscription(
            number="SUB-000001",
            customer_id=customer.id,
            plan_id=plan.id,
            status="active",
            start_date=date.today(),
            next_invoice_date=date.today(),
            payment_terms_days=14,
            is_paused=False,
            created_by=admin.id,
        )
        db.add(subscription)
        db.flush()
        line = SubscriptionLine(
            subscription_id=subscription.id,
            product_id=product.id,
            description=product.name,
            quantity=1,
            unit_price=product.sales_price + variant.extra_price,
            tax_id=tax.id,
        )
        db.add(line)
        db.flush()
        db.add(SubscriptionLineVariant(line_id=line.id, variant_value_id=variant.id))
        db.add(
            SubscriptionStatusHistory(
                subscription_id=subscription.id,
                from_status=None,
                to_status="active",
                changed_by=admin.id,
                changed_at=subscription.created_at,
            )
        )
        template = QuotationTemplate(name="Monthly Software", plan_id=plan.id, validity_days=30)
        db.add(template)
        db.flush()
        template_line = QuotationTemplateLine(template_id=template.id, product_id=product.id, quantity=1)
        db.add(template_line)
        db.flush()
        db.add(QuotationTemplateLineVariant(line_id=template_line.id, variant_value_id=variant.id))
        db.add_all(
            [
                PaymentMethod(name=method, is_active=True)
                for method in ("cash", "bank_transfer", "card", "upi", "cheque")
            ]
        )

    print(f"Demo data loaded. Admin login: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print(f"Customer login: customer@revo.local / {CUSTOMER_PASSWORD}")


if __name__ == "__main__":
    seed_demo_data()

