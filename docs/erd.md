# Revo database ERD

This diagram is generated from the SQLAlchemy models in `backend/app/models/core.py`. All entities use a bigint identity primary key and include `created_at` and `updated_at` timestamps unless the model is an append-only join/history row with the same base fields.

```mermaid
erDiagram
    USERS ||--o| CUSTOMERS : "customer login"
    USERS ||--o{ PASSWORD_RESET_TOKENS : "reset tokens"
    USERS ||--o{ SUBSCRIPTIONS : "created by"
    USERS ||--o{ SUBSCRIPTION_STATUS_HISTORY : "changed by"
    USERS ||--o{ PAYMENTS : "recorded by"
    USERS ||--o{ AI_RUNS : "requested by"
    TAXES ||--o{ PRODUCTS : "default tax"
    TAXES ||--o{ SUBSCRIPTION_LINES : "tax snapshot source"
    PRODUCTS ||--o{ PRODUCT_VARIANT_ATTRIBUTES : "has"
    PRODUCT_VARIANT_ATTRIBUTES ||--o{ PRODUCT_VARIANT_VALUES : "contains"
    PLANS ||--o{ QUOTATION_TEMPLATES : "uses"
    QUOTATION_TEMPLATES ||--o{ QUOTATION_TEMPLATE_LINES : "contains"
    PRODUCTS ||--o{ QUOTATION_TEMPLATE_LINES : "selected product"
    QUOTATION_TEMPLATE_LINES ||--o{ QUOTATION_TEMPLATE_LINE_VARIANTS : "selects"
    PRODUCT_VARIANT_VALUES ||--o{ QUOTATION_TEMPLATE_LINE_VARIANTS : "selected value"
    CUSTOMERS ||--o{ SUBSCRIPTIONS : "owns"
    PLANS ||--o{ SUBSCRIPTIONS : "prices"
    SUBSCRIPTIONS ||--o{ SUBSCRIPTION_LINES : "contains"
    PRODUCTS ||--o{ SUBSCRIPTION_LINES : "billed product"
    SUBSCRIPTION_LINES ||--o{ SUBSCRIPTION_LINE_VARIANTS : "selects"
    PRODUCT_VARIANT_VALUES ||--o{ SUBSCRIPTION_LINE_VARIANTS : "selected value"
    SUBSCRIPTIONS ||--o{ SUBSCRIPTION_STATUS_HISTORY : "history"
    DISCOUNTS ||--o{ DISCOUNT_PRODUCTS : "eligible products"
    PRODUCTS ||--o{ DISCOUNT_PRODUCTS : "discount applies"
    SUBSCRIPTIONS ||--o{ INVOICES : "billed as"
    CUSTOMERS ||--o{ INVOICES : "receives"
    INVOICES ||--o{ INVOICE_LINES : "contains"
    PRODUCTS ||--o{ INVOICE_LINES : "historical product"
    DISCOUNTS ||--o{ INVOICE_LINES : "discount snapshot source"
    INVOICES ||--o{ PAYMENTS : "paid by"
    PAYMENT_METHODS ||--o{ PAYMENTS : "method"

    USERS {
        bigint id PK
        string email UK
        string name
        string role
        boolean is_active
        int token_version
    }
    PASSWORD_RESET_TOKENS {
        bigint id PK
        bigint user_id FK
        string token_hash UK
        datetime expires_at
        datetime used_at
    }
    CUSTOMERS {
        bigint id PK
        bigint user_id FK_UK
        string name
        string email
        string phone
        string company
        string billing_address
        string tax_id
        boolean is_active
    }
    TAXES {
        bigint id PK
        string name UK
        decimal rate_pct
        boolean is_active
    }
    PRODUCTS {
        bigint id PK
        bigint default_tax_id FK
        string name
        string type
        decimal sales_price
        decimal cost_price
        boolean is_active
    }
    PRODUCT_VARIANT_ATTRIBUTES {
        bigint id PK
        bigint product_id FK
        string name
    }
    PRODUCT_VARIANT_VALUES {
        bigint id PK
        bigint attribute_id FK
        string value
        decimal extra_price
    }
    PLANS {
        bigint id PK
        string name
        decimal price
        string billing_period
        int min_quantity
        date available_from
        date available_to
        boolean auto_close
        boolean closable
        boolean pausable
        boolean renewable
        boolean is_active
    }
    QUOTATION_TEMPLATES {
        bigint id PK
        bigint plan_id FK
        string name
        int validity_days
    }
    QUOTATION_TEMPLATE_LINES {
        bigint id PK
        bigint template_id FK
        bigint product_id FK
        int quantity
    }
    QUOTATION_TEMPLATE_LINE_VARIANTS {
        bigint id PK
        bigint line_id FK
        bigint variant_value_id FK
    }
    SUBSCRIPTIONS {
        bigint id PK
        string number UK
        bigint customer_id FK
        bigint plan_id FK
        bigint created_by FK
        string status
        date start_date
        date expiry_date
        date next_invoice_date
        date quotation_expires_on
        boolean is_paused
    }
    SUBSCRIPTION_LINES {
        bigint id PK
        bigint subscription_id FK
        bigint product_id FK
        bigint tax_id FK
        string description
        int quantity
        decimal unit_price
    }
    SUBSCRIPTION_LINE_VARIANTS {
        bigint id PK
        bigint line_id FK
        bigint variant_value_id FK
    }
    SUBSCRIPTION_STATUS_HISTORY {
        bigint id PK
        bigint subscription_id FK
        bigint changed_by FK
        string from_status
        string to_status
        datetime changed_at
    }
    DISCOUNTS {
        bigint id PK
        string name
        string type
        decimal value
        string scope
        decimal min_purchase
        int min_quantity
        date start_date
        date end_date
        int max_uses
        int uses_count
        boolean is_active
    }
    DISCOUNT_PRODUCTS {
        bigint id PK
        bigint discount_id FK
        bigint product_id FK
    }
    INVOICES {
        bigint id PK
        string number UK
        bigint subscription_id FK
        bigint customer_id FK
        string status
        date invoice_date
        date due_date
        date period_start
        date period_end
        decimal total
        decimal amount_paid
        decimal amount_due
    }
    INVOICE_LINES {
        bigint id PK
        bigint invoice_id FK
        bigint product_id FK
        bigint discount_id FK
        string description
        int quantity
        decimal unit_price
        decimal variant_extra
        string discount_name
        decimal discount_amount
        string tax_name
        decimal tax_rate_pct
        decimal tax_amount
        decimal line_total
    }
    PAYMENT_METHODS {
        bigint id PK
        string name UK
        boolean is_active
    }
    PAYMENTS {
        bigint id PK
        bigint invoice_id FK
        bigint method_id FK
        bigint recorded_by FK
        decimal amount
        date paid_on
        string note
    }
    AI_RUNS {
        bigint id PK
        bigint user_id FK
        string agent
        string input
        json plan
        json tool_calls
        string output
        string model
        string provider
        int latency_ms
        int tokens_in
        int tokens_out
        string status
    }
    BRIEFS {
        bigint id PK
        date brief_date UK
        json payload
        string narrative
        string model
        string provider
        boolean used_fallback
    }
```

`invoice_lines` stores the price, discount, and tax details used at billing time. Those values are snapshots, so changes to catalog records do not rewrite issued invoice history.
