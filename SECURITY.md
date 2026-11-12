# Security policy

AMLNet is a synthetic-data research/demo application. Do not submit real banking records, credentials, database URLs, API keys, private keys, or customer information to the repository or issue tracker.

## Reporting

Please report suspected vulnerabilities privately to the repository owner through GitHub’s private security advisory flow rather than opening a public issue. Include reproduction steps, affected file/version, impact, and a suggested mitigation. Do not include secrets or personal data in a report.

## Secret handling

Use private environment variables for `DATABASE_URL`, `ADMIN_API_KEY`, `CORS_ORIGINS`, and hosting credentials. The repository’s `.env.example` files contain placeholders only. Rotate any credential that may have appeared in a shell history, log, screenshot, or public system.
