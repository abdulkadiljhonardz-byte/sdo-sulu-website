# SDO Sulu Digital Information Portal

A modular Django portal for official SDO Sulu news, school directory, issuances, downloadable resources, job vacancies, event listings, and public document verification.

## Quick start

1. `cp .env.example .env` and set a strong secret plus PostgreSQL `DATABASE_URL`.
2. `python3 -m venv .venv && .venv/bin/pip install -r requirements/base.txt`
3. `./.venv/bin/python manage.py migrate`
4. `./.venv/bin/python manage.py createsuperuser`
5. `./.venv/bin/python manage.py runserver`

SQLite is used only when `DATABASE_URL` is absent; use PostgreSQL in every shared or production environment.

## Railpack / Railway deployment

The repository includes a root `requirements.txt` for Python build detection and
an executable `start.sh` production entrypoint. The entrypoint applies database
migrations, collects static assets, and starts Gunicorn on the platform-provided
`PORT`.

Provision PostgreSQL and configure at least `DATABASE_URL`,
`DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, `DJANGO_ALLOWED_HOSTS`, and
`DJANGO_CSRF_TRUSTED_ORIGINS` in the deployment environment. Set the service
start command to `./start.sh` if it is not detected automatically. Uploaded
media requires a persistent volume or an object-storage backend because the
default PaaS filesystem is ephemeral.

## Security and operations

The settings enforce CSRF middleware, ORM-based queries, HttpOnly/SameSite cookies, secure cookies and HSTS outside debug mode, strong passwords, clickjacking protection, and safe storage names for service attachments. Keep `DEBUG=False`, do not commit `.env`, serve HTTPS through Nginx, and restrict media/private attachments at the application layer.

Public self-registration and transactional online services are disabled by default. Staff accounts are created by an administrator and support username/email authentication, profile and password management, internal notifications, and activity audit records. Existing request, appointment, and help-desk data is retained for authorized administration and is not deleted.

The custom Staff Portal includes **Users & Roles** at `/account/users/`. Only a Super Admin can create or update managed accounts. SDO Administrator and Office/Section Staff selections synchronize conservative backend permissions; the Super Admin role cannot be granted from this form and remains restricted to Django's secure superuser creation process.

Routine operations are handled inside the custom **System Administration** interface at `/dashboard/content/`. It manages users and roles, portal settings, offices, districts, issuances, news, downloads, events, vacancies, schools, verified documents, feedback and complaints, internal notifications, audit history, and read-only retained transactions. Every create/update operation performs a backend permission check and writes an audit entry. Issuance uploads additionally require a real PDF signature.

### Publishing and communications

- Configure `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL`, and `ADMIN_EMAILS` for the official SMTP account. Email delivery failures are logged without losing the underlying saved operation.
- Password resets use Django's signed, expiring reset-token workflow. New staff accounts, publishing approvals, complaint status changes, and login-limit security events generate email notices.
- Office/Section Staff must have an assigned office. Their custom administration lists and object lookups are filtered server-side to that office; submitted news, announcements, downloads, and issuances remain drafts until an Administrator publishes them.
- Replacing an issuance PDF requires a revision reason. The previous file, uploader, timestamp, and version number are preserved and available only through the permission-checked System Administration download route.
- About, Mission, Vision, Core Values, Officials, Organizational Structure, Privacy Policy, and Terms of Use are seeded as editable public pages and managed under **Public Information Pages**.
- News supports validated JPG/PNG cover photos. Its **Add** screen also accepts a public `facebook.com` or `fb.watch` post URL and copies the public caption and photo. Administrators can publish the import immediately; Office Staff imports remain drafts for review. Facebook may withhold metadata for private, age-restricted, login-only, or automation-blocked posts. In that case the portal refuses an incomplete import and the editor must enter the caption/photo manually.
- **Facebook News Sync** uses the official Meta Graph API for Page ID `100042494841401`. It imports and publishes image-backed Page posts dated 2026–2027, rejects memorandum labels, and prevents duplicate post IDs/permalinks. Configure the secret `FACEBOOK_PAGE_ACCESS_TOKEN` in `.env`; public profile HTML is not used as a feed and the token must never be committed.
- New memoranda use a concise publishing form with an official JPG/PNG cover picture and validated PDF attachment. There is no memorandum body/description editor; the public card uses the cover picture, reference, title, category, and issue date, while the full content remains in the downloadable PDF.

### Analytics, imports, reports, and safeguards

- `/dashboard/analytics/` reports live published-content totals, downloads, searches, school-directory activity, complaints, active staff, usage trends, top searches, and top news from the database. Analytics deliberately does not store visitor IP addresses.
- `/dashboard/data/` imports schools from CSV/XLSX and issuances from CSV/XLSX plus matching validated PDFs. Imports are atomic: any invalid or duplicate row prevents the entire dataset from being saved. Bulk issuances always begin as drafts.
- `/dashboard/reports/` filters real operational records and exports CSV, Excel-compatible XLSX, or an actual PDF document.
- Publication queries enforce scheduled start and expiration times. Administrators can preview records before publishing; archival requires a confirmed POST action. `python manage.py expire_publications` performs auditable cleanup and is scheduled hourly by the supplied production timer.
- Downloads pass through application endpoints so usage is counted. Nginx must expose only `/media/public/`; never configure a broad `/media/` alias.

`ENABLE_ONLINE_TRANSACTIONS=False` blocks all `/services/`, `/appointments/`, and `/helpdesk/` endpoints at the middleware layer. `ENABLE_PUBLIC_REGISTRATION=False` removes the public registration route. These controls are intentionally server-side and are not merely hidden navigation links.

## Publication checklist

- Set `DJANGO_DEBUG=False`, a unique `DJANGO_SECRET_KEY`, the real hostname, and `DJANGO_SECURE_SSL_REDIRECT=True`.
- Use PostgreSQL through `DATABASE_URL`; SQLite is for local development only.
- Configure a real SMTP backend and verified sender before enabling password-reset email in production.
- Run `python manage.py migrate`, `python manage.py collectstatic --noinput`, and `python manage.py check --deploy`.
- Serve only public static/media resources through Nginx. Private request and ticket files must use their permission-checked download views.
- Obtain an HTTPS certificate, restrict firewall ports to SSH/HTTP/HTTPS, and enable scheduled PostgreSQL plus uploaded-file backups.
- Create staff accounts individually, assign the minimum necessary portal role, and enable TOTP once the deployment's authenticator integration is configured.
- Run `python manage.py test` before each release and verify a restore from backups before launch.

For Ubuntu: follow [`deployment/DEPLOYMENT.md`](deployment/DEPLOYMENT.md). The deployment package includes hardened Gunicorn and Nginx configurations, HTTPS-only routing, a database-backed health endpoint, daily checksummed PostgreSQL/media backups, a guarded restore-test script, hourly publication expiration, journald/error-email logging, and five-minute local health monitoring. Encrypted off-host backup replication and an external uptime monitor must be configured by the deployment operator.

## Modules

`accounts`, `offices`, `schools`, `content`, `issuances`, `services`, `appointments`, `tickets`, `feedback`, `vacancies`, `events`, `verification`, `notifications`, and `audit` are isolated Django apps. Use the custom Staff Portal for normal administration; `/secure-admin/` remains an emergency superuser backstop only.
