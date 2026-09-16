# Production deployment runbook

This runbook targets Ubuntu, PostgreSQL, Gunicorn, Nginx, and Let's Encrypt. Replace `portal.example.gov.ph` in the supplied service and Nginx files before installation.

## 1. Host preparation

Install Python, PostgreSQL, Nginx, Certbot, Git, build tools, `curl`, and `ufw`. Create `/srv/sdo-sulu`, deploy the repository there, create a virtual environment, and install the pinned `requirements/production.txt`. The application directory should be owned by the deployment operator, while `/srv/sdo-sulu/media` must be writable by `www-data` and not world-readable.

Create a dedicated PostgreSQL database and least-privilege login. Require password authentication over localhost and use a long generated password. Configure `DATABASE_URL` in `/srv/sdo-sulu/.env`; never commit that file.

Example database creation (replace the prompted password with a generated secret):

```sql
CREATE ROLE sdo_sulu LOGIN PASSWORD '<generated-password>';
CREATE DATABASE sdo_sulu OWNER sdo_sulu ENCODING 'UTF8';
REVOKE ALL ON DATABASE sdo_sulu FROM PUBLIC;
GRANT CONNECT, TEMPORARY ON DATABASE sdo_sulu TO sdo_sulu;
```

Keep PostgreSQL on `127.0.0.1`, use `scram-sha-256` authentication in `pg_hba.conf`, and restart PostgreSQL after validating its configuration.

Required production values include:

```dotenv
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<long-random-value>
DJANGO_ALLOWED_HOSTS=portal.example.gov.ph
DJANGO_CSRF_TRUSTED_ORIGINS=https://portal.example.gov.ph
DJANGO_SECURE_SSL_REDIRECT=True
DATABASE_URL=postgresql://sdo_sulu:<password>@127.0.0.1:5432/sdo_sulu
ENABLE_ONLINE_TRANSACTIONS=False
ENABLE_PUBLIC_REGISTRATION=False
```

Configure the official SMTP variables shown in `.env.example`. Protect the file with mode `0640`, owner `root`, and group `www-data`.

## 2. Release procedure

Run these commands from `/srv/sdo-sulu` inside the virtual environment:

```bash
python manage.py check --deploy
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py test
```

Install `deployment/sdo-sulu.service` under `/etc/systemd/system/`, then enable and start it. Before enabling the supplied TLS Nginx file, obtain the first certificate with a temporary HTTP virtual host or Certbot standalone mode. Then install the Nginx configuration under `/etc/nginx/sites-available/sdo-sulu`, update its hostname and certificate paths, enable it, run `nginx -t`, and reload Nginx.

One first-certificate option is:

```bash
sudo systemctl stop nginx
sudo certbot certonly --standalone -d portal.example.gov.ph
sudo systemctl start nginx
sudo certbot renew --dry-run
```

The supplied Nginx configuration exposes only static assets and `/media/public/`. Private request/ticket files and historical issuance versions must never be served with a broad `/media/` alias.

## 3. Firewall and operating system

Allow only OpenSSH, HTTP, and HTTPS through UFW:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

Restrict SSH to administrator source networks when possible, disable password SSH login after key access is verified, install unattended security upgrades, and keep PostgreSQL bound to localhost unless a private database network is intentionally used.

## 4. Backups and restore testing

Install `backup.sh` as executable. Create `/var/backups/sdo-sulu` owned by `www-data` with mode `0700`. Install and enable `sdo-sulu-backup.timer`. It creates a PostgreSQL custom-format dump, a media archive, and SHA-256 checksums, then removes backup directories older than `BACKUP_RETENTION_DAYS` (default 30).

```bash
sudo install -o www-data -g www-data -m 0700 -d /var/backups/sdo-sulu
sudo install -m 0644 deployment/sdo-sulu-backup.service deployment/sdo-sulu-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sdo-sulu-backup.timer
sudo systemctl start sdo-sulu-backup.service
sudo systemctl status sdo-sulu-backup.service
```

Copy backups to encrypted off-host storage. The local timer alone is not disaster recovery.

At least monthly, provision a disposable PostgreSQL database whose name ends with `_restore_test`, set `RESTORE_TEST_DATABASE_URL`, and run:

```bash
sudo -u www-data /srv/sdo-sulu/deployment/restore-test.sh
```

The script validates checksums, recreates only the disposable database schema, restores the dump, checks the migration table, and extracts media into a temporary directory. Never point it at the production database.

For an approved production restore, stop Gunicorn, take a safety backup, verify checksums, restore the selected database dump with `pg_restore`, restore `media.tar.gz` into `/srv/sdo-sulu/media`, correct ownership, run migrations, and restart the service. Document the incident and exact backup identifier.

## 5. Scheduled publication maintenance

Install and enable `sdo-sulu-maintenance.timer`. It runs `manage.py expire_publications` hourly and records an audit event when records are archived. Public queries independently enforce publication and expiration times, so delayed timer execution does not expose expired content.

## 6. Monitoring and logs

### Official Facebook News synchronization

Create an official Meta Page access token with the permissions required to read the SDO Sulu Page posts. Set `FACEBOOK_PAGE_ACCESS_TOKEN` only in `/srv/sdo-sulu/.env`; never commit or display it. Keep `FACEBOOK_PAGE_ID=100042494841401`. Test manually with `sudo -u www-data /srv/sdo-sulu/.venv/bin/python manage.py sync_facebook_news --draft`, review the imported drafts, then install and enable the daily synchronization:

```bash
sudo install -m 0644 deployment/sdo-sulu-facebook-sync.service deployment/sdo-sulu-facebook-sync.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sdo-sulu-facebook-sync.timer
```

The sync accepts only 2026–2027 posts from the configured Page endpoint, rejects memorandum captions, requires public caption/image/permalink metadata, skips duplicates, and records a system audit entry. Rotate the token according to the official Meta application policy and alert on timer failures.

The unauthenticated `/health/` endpoint performs a database query and returns only component status. Install `sdo-sulu-health.service` and `.timer`, replace the hostname, and enable the timer. Connect the same HTTPS endpoint to an external uptime monitor so alerts still work during a total server outage.

Gunicorn and Django log to the systemd journal. Review with `journalctl -u sdo-sulu`; forward logs to a protected centralized logging/error-monitoring service in production. Alert on repeated 5xx responses, failed health checks, backup failures, high disk utilization, certificate-renewal failure, and repeated authentication lockouts.

## 7. Release rollback

Keep the previous application release and its dependency lock available. Database migrations should be reviewed before deployment. If rollback is required, stop traffic, restore the matching database/media backup when schema changes are incompatible, activate the previous release, collect its static files, and restart Gunicorn. Validate `/health/`, staff login, an issuance download, and the public homepage before reopening service.
