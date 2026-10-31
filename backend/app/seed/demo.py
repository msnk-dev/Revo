from datetime import date
from decimal import Decimal
import argparse
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

ADMIN_EMAIL = "admin@example.com"


def _compliant_password(value: str) -> bool:
    return (
        len(value) >= 9
        and any(char.isupper() for char in value)
        and any(char.islower() for char in value)
        and any(not char.isalnum() for char in value)
    )


def _new_demo_password() -> str:
    # The fixed suffix guarantees upper, lower, special, and length rules.
    return f"{secrets.token_urlsafe(24)}aA!"


ADMIN_PASSWORD = os.environ.get("REVO_DEMO_ADMIN_PASSWORD") or _new_demo_password()
CUSTOMER_PASSWORD = os.environ.get("REVO_DEMO_CUSTOMER_PASSWORD") or _new_demo_password()
LEGACY_DEMO_ADMIN_PASSWORD = "admin123"
LEGACY_DEMO_CUSTOMER_PASSWORD = "user123"


def seed_demo_data(*, reset_credentials: bool = False, use_legacy_demo_passwords: bool = False) -> None:
    admin_password, customer_password = ADMIN_PASSWORD, CUSTOMER_PASSWORD
    if use_legacy_demo_passwords:
        from app.config import settings

        if settings.app_env.lower() != "demo":
            raise RuntimeError("Weak demo passwords can only be loaded when APP_ENV=demo")
        admin_password, customer_password = LEGACY_DEMO_ADMIN_PASSWORD, LEGACY_DEMO_CUSTOMER_PASSWORD
    else:
        for env_name, password in (
            ("REVO_DEMO_ADMIN_PASSWORD", admin_password),
            ("REVO_DEMO_CUSTOMER_PASSWORD", customer_password),
        ):
            if not _compliant_password(password):
                raise RuntimeError(f"{env_name} must be at least 9 characters and include uppercase, lowercase, and special characters")

    hasher = PasswordHasher()
    if reset_credentials:
        with SessionLocal.begin() as db:
            admin = db.scalar(select(User).where(func.lower(User.email) == ADMIN_EMAIL))
            customer = db.scalar(select(User).where(func.lower(User.email) == "customer@example.com"))
            if admin is None or customer is None:
                raise RuntimeError("Cannot reset demo credentials: seed the demo accounts first")
            admin.password_hash = hasher.hash(admin_password)
            admin.token_version += 1
            customer.password_hash = hasher.hash(customer_password)
            customer.token_version += 1
        print("Existing demo credentials were reset and all previous sessions invalidated.")
        print(f"Admin login: {ADMIN_EMAIL} / {admin_password}")
        print(f"Customer login: customer@example.com / {customer_password}")
        return

    with SessionLocal.begin() as db:
        existing = db.scalar(select(User).where(func.lower(User.email) == ADMIN_EMAIL))
        if existing:
            print(f"Demo data already exists. Admin login: {ADMIN_EMAIL}; the original password is unchanged.")
            return

        admin = User(email=ADMIN_EMAIL, password_hash=hasher.hash(admin_password), role="admin", is_active=True)
        customer_user = User(
            email="customer@example.com",
            password_hash=hasher.hash(customer_password),
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

    print(f"Demo data loaded. Admin login: {ADMIN_EMAIL} / {admin_password}")
    print(f"Customer login: customer@example.com / {customer_password}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load Revo's local demo fixtures")
    parser.add_argument("--reset-credentials", action="store_true", help="rotate existing demo passwords and revoke old sessions")
    parser.add_argument("--use-legacy-demo-passwords", action="store_true", help="use admin123/user123 only with APP_ENV=demo")
    arguments = parser.parse_args()
    seed_demo_data(reset_credentials=arguments.reset_credentials, use_legacy_demo_passwords=arguments.use_legacy_demo_passwords)

