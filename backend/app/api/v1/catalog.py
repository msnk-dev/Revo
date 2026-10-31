from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.deps import Actor, get_current_actor, get_db, require_roles
from app.schemas.catalog import (
    PaymentMethodIn,
    PaymentMethodListOut,
    PaymentMethodOut,
    PlanCreateIn,
    PlanListOut,
    PlanOut,
    ProductCreateIn,
    ProductListOut,
    ProductOut,
    QuotationTemplateIn,
    QuotationTemplateListOut,
    QuotationTemplateOut,
    TaxCreateIn,
    TaxListOut,
    TaxOut,
    VariantAttributeIn,
    VariantAttributeOut,
)
from app.services import catalog as catalog_service

router = APIRouter(tags=["catalog"])
DbSession = Annotated[Session, Depends(get_db)]
AdminActor = Annotated[Actor, Depends(require_roles("admin"))]
AdminOrStaffActor = Annotated[Actor, Depends(require_roles("admin", "staff"))]
AnyActor = Annotated[Actor, Depends(get_current_actor)]


@router.get("/products", response_model=ProductListOut)
def list_products(
    db: DbSession,
    actor: AnyActor,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    q: str | None = Query(default=None, min_length=1, max_length=100),
) -> ProductListOut:
    items, total = catalog_service.list_products(db, actor, page, page_size, q)
    return ProductListOut(items=items, total=total, page=page, page_size=page_size)


@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreateIn, db: DbSession, actor: AdminActor) -> ProductOut:
    return catalog_service.create_product(db, payload)


@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: Annotated[int, Path(gt=0)], db: DbSession, actor: AnyActor) -> ProductOut:
    return catalog_service.get_product(db, actor, product_id)


@router.put("/products/{product_id}", response_model=ProductOut)
def update_product(
    product_id: Annotated[int, Path(gt=0)],
    payload: ProductCreateIn,
    db: DbSession,
    actor: AdminActor,
) -> ProductOut:
    return catalog_service.update_product(db, product_id, payload)


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_product(
    product_id: Annotated[int, Path(gt=0)],
    db: DbSession,
    actor: AdminActor,
) -> Response:
    catalog_service.deactivate_product(db, product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/products/{product_id}/variants", response_model=list[VariantAttributeOut])
def list_product_variants(
    product_id: Annotated[int, Path(gt=0)],
    db: DbSession,
    actor: AnyActor,
) -> list[VariantAttributeOut]:
    return catalog_service.list_product_variants(db, actor, product_id)


@router.post(
    "/products/{product_id}/variants",
    response_model=VariantAttributeOut,
    status_code=status.HTTP_201_CREATED,
)
def create_product_variants(
    product_id: Annotated[int, Path(gt=0)],
    payload: VariantAttributeIn,
    db: DbSession,
    actor: AdminActor,
) -> VariantAttributeOut:
    return catalog_service.create_product_variants(db, product_id, payload)


@router.get("/taxes", response_model=TaxListOut)
def list_taxes(
    db: DbSession,
    actor: AdminOrStaffActor,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    q: str | None = Query(default=None, min_length=1, max_length=100),
) -> TaxListOut:
    items, total = catalog_service.list_taxes(db, page, page_size, q)
    return TaxListOut(items=items, total=total, page=page, page_size=page_size)


@router.post("/taxes", response_model=TaxOut, status_code=status.HTTP_201_CREATED)
def create_tax(payload: TaxCreateIn, db: DbSession, actor: AdminActor) -> TaxOut:
    return catalog_service.create_tax(db, payload)


@router.get("/taxes/{tax_id}", response_model=TaxOut)
def get_tax(tax_id: Annotated[int, Path(gt=0)], db: DbSession, actor: AdminOrStaffActor) -> TaxOut:
    return catalog_service.get_tax(db, tax_id)


@router.put("/taxes/{tax_id}", response_model=TaxOut)
def update_tax(
    tax_id: Annotated[int, Path(gt=0)],
    payload: TaxCreateIn,
    db: DbSession,
    actor: AdminActor,
) -> TaxOut:
    return catalog_service.update_tax(db, tax_id, payload)


@router.delete("/taxes/{tax_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_tax(tax_id: Annotated[int, Path(gt=0)], db: DbSession, actor: AdminActor) -> Response:
    catalog_service.deactivate_tax(db, tax_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/plans", response_model=PlanListOut)
def list_plans(
    db: DbSession,
    actor: AnyActor,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    q: str | None = Query(default=None, min_length=1, max_length=100),
) -> PlanListOut:
    items, total = catalog_service.list_plans(db, actor, page, page_size, q)
    return PlanListOut(items=items, total=total, page=page, page_size=page_size)


@router.post("/plans", response_model=PlanOut, status_code=status.HTTP_201_CREATED)
def create_plan(payload: PlanCreateIn, db: DbSession, actor: AdminActor) -> PlanOut:
    return catalog_service.create_plan(db, payload)


@router.get("/plans/{plan_id}", response_model=PlanOut)
def get_plan(plan_id: Annotated[int, Path(gt=0)], db: DbSession, actor: AnyActor) -> PlanOut:
    return catalog_service.get_plan(db, actor, plan_id)


@router.put("/plans/{plan_id}", response_model=PlanOut)
def update_plan(
    plan_id: Annotated[int, Path(gt=0)],
    payload: PlanCreateIn,
    db: DbSession,
    actor: AdminActor,
) -> PlanOut:
    return catalog_service.update_plan(db, plan_id, payload)


@router.delete("/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_plan(plan_id: Annotated[int, Path(gt=0)], db: DbSession, actor: AdminActor) -> Response:
    catalog_service.deactivate_plan(db, plan_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/payment-methods", response_model=PaymentMethodListOut)
def list_payment_methods(
    db: DbSession,
    actor: AdminOrStaffActor,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    q: str | None = Query(default=None, min_length=1, max_length=100),
) -> PaymentMethodListOut:
    items, total = catalog_service.list_payment_methods(db, page, page_size, q)
    return PaymentMethodListOut(items=items, total=total, page=page, page_size=page_size)


@router.post("/payment-methods", response_model=PaymentMethodOut, status_code=status.HTTP_201_CREATED)
def create_payment_method(payload: PaymentMethodIn, db: DbSession, actor: AdminActor) -> PaymentMethodOut:
    return catalog_service.create_payment_method(db, payload)


@router.put("/payment-methods/{method_id}", response_model=PaymentMethodOut)
def update_payment_method(
    method_id: Annotated[int, Path(gt=0)],
    payload: PaymentMethodIn,
    db: DbSession,
    actor: AdminActor,
) -> PaymentMethodOut:
    return catalog_service.update_payment_method(db, method_id, payload)


@router.delete("/payment-methods/{method_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_payment_method(
    method_id: Annotated[int, Path(gt=0)],
    db: DbSession,
    actor: AdminActor,
) -> Response:
    catalog_service.deactivate_payment_method(db, method_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/quotation-templates", response_model=QuotationTemplateListOut)
def list_quotation_templates(
    db: DbSession,
    actor: AdminOrStaffActor,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    q: str | None = Query(default=None, min_length=1, max_length=100),
) -> QuotationTemplateListOut:
    items, total = catalog_service.list_quotation_templates(db, page, page_size, q)
    return QuotationTemplateListOut(items=items, total=total, page=page, page_size=page_size)


@router.post(
    "/quotation-templates",
    response_model=QuotationTemplateOut,
    status_code=status.HTTP_201_CREATED,
)
def create_quotation_template(
    payload: QuotationTemplateIn,
    db: DbSession,
    actor: AdminActor,
) -> QuotationTemplateOut:
    return catalog_service.create_quotation_template(db, payload)


@router.get("/quotation-templates/{template_id}", response_model=QuotationTemplateOut)
def get_quotation_template(
    template_id: Annotated[int, Path(gt=0)],
    db: DbSession,
    actor: AdminOrStaffActor,
) -> QuotationTemplateOut:
    return catalog_service.get_quotation_template(db, template_id)


@router.put("/quotation-templates/{template_id}", response_model=QuotationTemplateOut)
def update_quotation_template(
    template_id: Annotated[int, Path(gt=0)],
    payload: QuotationTemplateIn,
    db: DbSession,
    actor: AdminActor,
) -> QuotationTemplateOut:
    return catalog_service.update_quotation_template(db, template_id, payload)


@router.delete("/quotation-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quotation_template(
    template_id: Annotated[int, Path(gt=0)],
    db: DbSession,
    actor: AdminActor,
) -> Response:
    catalog_service.delete_quotation_template(db, template_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

