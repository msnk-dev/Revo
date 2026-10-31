# Backend decisions

## Block 0

- Use synchronous SQLAlchemy sessions with PostgreSQL because the scheduler and billing transactions depend on explicit row locks.
- Use bigint-style integer identity keys and join tables for selected product variants, keeping referential integrity and allowing variant choices to be queried without array parsing.
- Keep the Block 0 service functions as fixed fixtures until their milestone replaces them; interfaces stay stable for Person B's AI tools.
- Use ReportLab for local PDF generation and stdlib SMTP for MailHog email to avoid a browser/system-library dependency in the API container.

