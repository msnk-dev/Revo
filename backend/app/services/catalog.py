from decimal import Decimal
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.deps import Actor
from app.errors import ConflictError, NotFoundError, ValidationFailed
from app.models import (
    PaymentMethod,
    Plan,
    Product,
    ProductVariantAttribute,
    ProductVariantValue,
    QuotationTemplate,
    QuotationTemplateLine,
    QuotationTemplateLineVariant,
    Tax,
)
from app.schemas.catalog import (
    PaymentMethodIn,
    PlanCreateIn,
    ProductCreateIn,
    QuotationTemplateIn,
    TaxCreateIn,
    VariantAttributeIn,
)


def _commit(db: Session, field: str | None = None) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        details = {field: "Conflicts with an existing value or reference"} if field else {}
        raise ConflictError("The catalog record conflicts with an existing record or reference", details) from exc


def _validate_product_reference(db: Session, tax_id: int | None) -> None:
    if tax_id is not None:
        tax = db.get(Tax, tax_id)
        if tax is None or not tax.is_active:
            raise ValidationFailed("The selected tax is unavailable", {"default_tax_id": "Unknown or inactive tax"})


def _page_query(db: Session, base_query, count_query, page: int, page_size: int):
    total = db.scalar(count_query) or 0
    items = list(db.scalars(base_query.offset((page - 1) * page_size).limit(page_size)))
    return items, total


def _visible_product(db: Session, actor: Actor, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None or (actor.role == "customer" and not product.is_active):
        raise NotFoundError("Product not found")
    return product


def list_products(db: Session, actor: Actor, page: int, page_size: int, q: str | None):
    query = select(Product)
    count = select(func.count()).select_from(Product)
    if actor.role == "customer":
        query = query.where(Product.is_active.is_(True))
        count = count.where(Product.is_active.is_(True))
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(Product.name.ilike(pattern))
        count = count.where(Product.name.ilike(pattern))
    return _page_query(db, query.order_by(Product.name, Product.id), count, page, page_size)


def get_product(db: Session, actor: Actor, product_id: int) -> Product:
    return _visible_product(db, actor, product_id)


def create_product(db: Session, payload: ProductCreateIn) -> Product:
    _validate_product_reference(db, payload.default_tax_id)
    product = Product(**payload.model_dump(), is_active=True)
    db.add(product)
    _commit(db)
    db.refresh(product)
    return product


def update_product(db: Session, product_id: int, payload: ProductCreateIn) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise NotFoundError("Product not found")
    _validate_product_reference(db, payload.default_tax_id)
    for field, value in payload.model_dump().items():
        setattr(product, field, value)
    _commit(db, "name")
    db.refresh(product)
    return product


def deactivate_product(db: Session, product_id: int) -> None:
    product = db.get(Product, product_id)
    if product is None:
        raise NotFoundError("Product not found")
    product.is_active = False
    _commit(db)


def list_product_variants(db: Session, actor: Actor, product_id: int) -> list[dict[str, Any]]:
    _visible_product(db, actor, product_id)
    attributes = list(
        db.scalars(
            select(ProductVariantAttribute)
            .where(ProductVariantAttribute.product_id == product_id)
            .order_by(ProductVariantAttribute.name, ProductVariantAttribute.id)
        )
    )
    result = []
    for attribute in attributes:
        values = list(
            db.scalars(
                select(ProductVariantValue)
                .where(ProductVariantValue.attribute_id == attribute.id)
                .order_by(ProductVariantValue.value, ProductVariantValue.id)
            )
        )
        result.append(
            {
                "id": attribute.id,
                "product_id": product_id,
                "name": attribute.name,
                "values": values,
            }
        )
    return result


def create_product_variants(db: Session, product_id: int, payload: VariantAttributeIn) -> dict[str, Any]:
    product = db.get(Product, product_id)
    if product is None:
        raise NotFoundError("Product not found")
    attribute = ProductVariantAttribute(product_id=product_id, name=payload.name)
    db.add(attribute)
    db.flush()
    for value in payload.values:
        db.add(
            ProductVariantValue(
                attribute_id=attribute.id,
                value=value.value,
                extra_price=value.extra_price,
            )
        )
    _commit(db)
    db.refresh(attribute)
    return {
        "id": attribute.id,
        "product_id": product_id,
        "name": attribute.name,
        "values": list(
            db.scalars(
                select(ProductVariantValue)
                .where(ProductVariantValue.attribute_id == attribute.id)
                .order_by(ProductVariantValue.id)
            )
        ),
    }


def calculate_unit_price(db: Session, product_id: int, variant_value_ids: list[int]) -> Decimal:
    product = db.get(Product, product_id)
    if product is None:
        raise NotFoundError("Product not found")
    if len(variant_value_ids) != len(set(variant_value_ids)):
        raise ValidationFailed("Variant values must be unique", {"variant_value_ids": "Duplicate variant value"})
    if not variant_value_ids:
        return product.sales_price
    values = list(
        db.scalars(
            select(ProductVariantValue)
            .join(ProductVariantAttribute, ProductVariantAttribute.id == ProductVariantValue.attribute_id)
            .where(
                ProductVariantAttribute.product_id == product_id,
                ProductVariantValue.id.in_(variant_value_ids),
            )
        )
    )
    if len(values) != len(variant_value_ids):
        raise ValidationFailed("One or more variants do not belong to the product", {"variant_value_ids": "Invalid variant"})
    return product.sales_price + sum((value.extra_price for value in values), Decimal("0.00"))


def list_taxes(db: Session, page: int, page_size: int, q: str | None):
    query = select(Tax)
    count = select(func.count()).select_from(Tax)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(Tax.name.ilike(pattern))
        count = count.where(Tax.name.ilike(pattern))
    return _page_query(db, query.order_by(Tax.name, Tax.id), count, page, page_size)


def get_tax(db: Session, tax_id: int) -> Tax:
    tax = db.get(Tax, tax_id)
    if tax is None:
        raise NotFoundError("Tax not found")
    return tax


def create_tax(db: Session, payload: TaxCreateIn) -> Tax:
    tax = Tax(**payload.model_dump(), is_active=True)
    db.add(tax)
    _commit(db, "name")
    db.refresh(tax)
    return tax


def update_tax(db: Session, tax_id: int, payload: TaxCreateIn) -> Tax:
    tax = get_tax(db, tax_id)
    tax.name = payload.name
    tax.rate_pct = payload.rate_pct
    _commit(db, "name")
    db.refresh(tax)
    return tax


def deactivate_tax(db: Session, tax_id: int) -> None:
    tax = get_tax(db, tax_id)
    tax.is_active = False
    _commit(db)


def _visible_plan(db: Session, actor: Actor, plan_id: int) -> Plan:
    plan = db.get(Plan, plan_id)
    if plan is None or (actor.role == "customer" and not plan.is_active):
        raise NotFoundError("Plan not found")
    return plan


def list_plans(db: Session, actor: Actor, page: int, page_size: int, q: str | None):
    query = select(Plan)
    count = select(func.count()).select_from(Plan)
    if actor.role == "customer":
        query = query.where(Plan.is_active.is_(True))
        count = count.where(Plan.is_active.is_(True))
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(Plan.name.ilike(pattern))
        count = count.where(Plan.name.ilike(pattern))
    return _page_query(db, query.order_by(Plan.name, Plan.id), count, page, page_size)


def get_plan(db: Session, actor: Actor, plan_id: int) -> Plan:
    return _visible_plan(db, actor, plan_id)


def create_plan(db: Session, payload: PlanCreateIn) -> Plan:
    plan = Plan(**payload.model_dump(), is_active=True)
    db.add(plan)
    _commit(db)
    db.refresh(plan)
    return plan


def update_plan(db: Session, plan_id: int, payload: PlanCreateIn) -> Plan:
    plan = db.get(Plan, plan_id)
    if plan is None:
        raise NotFoundError("Plan not found")
    for field, value in payload.model_dump().items():
        setattr(plan, field, value)
    _commit(db)
    db.refresh(plan)
    return plan


def deactivate_plan(db: Session, plan_id: int) -> None:
    plan = db.get(Plan, plan_id)
    if plan is None:
        raise NotFoundError("Plan not found")
    plan.is_active = False
    _commit(db)


def plan_is_available(plan: Plan, on_date) -> bool:
    return (
        plan.is_active
        and (plan.available_from is None or plan.available_from <= on_date)
        and (plan.available_to is None or plan.available_to >= on_date)
    )


def list_payment_methods(db: Session, page: int, page_size: int, q: str | None):
    query = select(PaymentMethod)
    count = select(func.count()).select_from(PaymentMethod)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(PaymentMethod.name.ilike(pattern))
        count = count.where(PaymentMethod.name.ilike(pattern))
    return _page_query(db, query.order_by(PaymentMethod.name, PaymentMethod.id), count, page, page_size)


def create_payment_method(db: Session, payload: PaymentMethodIn) -> PaymentMethod:
    method = PaymentMethod(name=payload.name, is_active=True)
    db.add(method)
    _commit(db, "name")
    db.refresh(method)
    return method


def update_payment_method(db: Session, method_id: int, payload: PaymentMethodIn) -> PaymentMethod:
    method = db.get(PaymentMethod, method_id)
    if method is None:
        raise NotFoundError("Payment method not found")
    method.name = payload.name
    _commit(db, "name")
    db.refresh(method)
    return method


def deactivate_payment_method(db: Session, method_id: int) -> None:
    method = db.get(PaymentMethod, method_id)
    if method is None:
        raise NotFoundError("Payment method not found")
    method.is_active = False
    _commit(db)


def _template_dict(db: Session, template: QuotationTemplate) -> dict[str, Any]:
    return _template_dicts(db, [template])[0]


def _template_dicts(db: Session, templates: list[QuotationTemplate]) -> list[dict[str, Any]]:
    if not templates:
        return []
    template_ids = [template.id for template in templates]
    lines = list(db.scalars(select(QuotationTemplateLine).where(QuotationTemplateLine.template_id.in_(template_ids)).order_by(QuotationTemplateLine.id)))
    line_ids = [line.id for line in lines]
    variants: dict[int, list[int]] = {line_id: [] for line_id in line_ids}
    if line_ids:
        for line_id, value_id in db.execute(
            select(QuotationTemplateLineVariant.line_id, QuotationTemplateLineVariant.variant_value_id)
            .where(QuotationTemplateLineVariant.line_id.in_(line_ids)).order_by(QuotationTemplateLineVariant.id)
        ):
            variants[line_id].append(value_id)
    lines_by_template: dict[int, list[dict[str, Any]]] = {template_id: [] for template_id in template_ids}
    for line in lines:
        lines_by_template[line.template_id].append({
            "id": line.id, "product_id": line.product_id, "quantity": line.quantity,
            "variant_value_ids": variants[line.id],
        })
    return [{"id": template.id, "name": template.name, "plan_id": template.plan_id,
             "validity_days": template.validity_days, "lines": lines_by_template[template.id]}
            for template in templates]


def list_quotation_templates(db: Session, page: int, page_size: int, q: str | None):
    query = select(QuotationTemplate)
    count = select(func.count()).select_from(QuotationTemplate)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(QuotationTemplate.name.ilike(pattern))
        count = count.where(QuotationTemplate.name.ilike(pattern))
    items, total = _page_query(db, query.order_by(QuotationTemplate.name, QuotationTemplate.id), count, page, page_size)
    return _template_dicts(db, items), total


def get_quotation_template(db: Session, template_id: int) -> dict[str, Any]:
    template = db.get(QuotationTemplate, template_id)
    if template is None:
        raise NotFoundError("Quotation template not found")
    return _template_dict(db, template)


def _validate_template_lines(db: Session, payload: QuotationTemplateIn) -> None:
    if db.get(Plan, payload.plan_id) is None:
        raise ValidationFailed("The selected plan does not exist", {"plan_id": "Unknown plan"})
    for index, line in enumerate(payload.lines):
        product = db.get(Product, line.product_id)
        if product is None or not product.is_active:
            raise ValidationFailed("A template product is unavailable", {f"lines.{index}.product_id": "Unknown product"})
        try:
            calculate_unit_price(db, line.product_id, line.variant_value_ids)
        except ValidationFailed as exc:
            raise ValidationFailed(str(exc), {f"lines.{index}.variant_value_ids": "Invalid variant selection"}) from exc


def _write_template_lines(db: Session, template_id: int, payload: QuotationTemplateIn) -> None:
    for line in payload.lines:
        template_line = QuotationTemplateLine(
            template_id=template_id,
            product_id=line.product_id,
            quantity=line.quantity,
        )
        db.add(template_line)
        db.flush()
        for variant_value_id in line.variant_value_ids:
            db.add(
                QuotationTemplateLineVariant(
                    line_id=template_line.id,
                    variant_value_id=variant_value_id,
                )
            )


def create_quotation_template(db: Session, payload: QuotationTemplateIn) -> dict[str, Any]:
    _validate_template_lines(db, payload)
    template = QuotationTemplate(
        name=payload.name,
        plan_id=payload.plan_id,
        validity_days=payload.validity_days,
    )
    db.add(template)
    db.flush()
    _write_template_lines(db, template.id, payload)
    _commit(db)
    db.refresh(template)
    return _template_dict(db, template)


def update_quotation_template(db: Session, template_id: int, payload: QuotationTemplateIn) -> dict[str, Any]:
    template = db.get(QuotationTemplate, template_id)
    if template is None:
        raise NotFoundError("Quotation template not found")
    _validate_template_lines(db, payload)
    template.name = payload.name
    template.plan_id = payload.plan_id
    template.validity_days = payload.validity_days
    line_ids = select(QuotationTemplateLine.id).where(QuotationTemplateLine.template_id == template_id)
    db.execute(delete(QuotationTemplateLineVariant).where(QuotationTemplateLineVariant.line_id.in_(line_ids)))
    db.execute(delete(QuotationTemplateLine).where(QuotationTemplateLine.template_id == template_id))
    _write_template_lines(db, template_id, payload)
    _commit(db)
    db.refresh(template)
    return _template_dict(db, template)


def delete_quotation_template(db: Session, template_id: int) -> None:
    template = db.get(QuotationTemplate, template_id)
    if template is None:
        raise NotFoundError("Quotation template not found")
    line_ids = select(QuotationTemplateLine.id).where(QuotationTemplateLine.template_id == template_id)
    db.execute(delete(QuotationTemplateLineVariant).where(QuotationTemplateLineVariant.line_id.in_(line_ids)))
    db.execute(delete(QuotationTemplateLine).where(QuotationTemplateLine.template_id == template_id))
    db.delete(template)
    _commit(db)

