import os
from pathlib import Path
from urllib.parse import urlparse
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv
BASE_DIR=Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR/".env")
IS_RAILWAY=bool(os.environ.get("RAILWAY_ENVIRONMENT"))
# Development is the safe default for a fresh local checkout. Production
# deployments must explicitly set DJANGO_DEBUG=False in their environment.
DEBUG=os.environ.get("DJANGO_DEBUG","False" if IS_RAILWAY else "True").lower()=="true"
SECRET_KEY=os.environ.get("DJANGO_SECRET_KEY","")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY="unsafe-development-key-change-me"
    else:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be configured in production.")
ALLOWED_HOSTS=[x.strip() for x in os.environ.get("DJANGO_ALLOWED_HOSTS","localhost,127.0.0.1").split(",") if x.strip()]
RAILWAY_PUBLIC_DOMAIN=os.environ.get("RAILWAY_PUBLIC_DOMAIN","").strip()
if RAILWAY_PUBLIC_DOMAIN:
    ALLOWED_HOSTS.append(RAILWAY_PUBLIC_DOMAIN)
# Railway uses this hostname for deployment health checks.
if not DEBUG:
    ALLOWED_HOSTS.append("healthcheck.railway.app")
# The deployed portal is informational by default. Historical transactional
# records remain available to authorized administrators, but their public
# submission endpoints are not mounted unless explicitly enabled.
ENABLE_ONLINE_TRANSACTIONS=os.environ.get("ENABLE_ONLINE_TRANSACTIONS","False").lower()=="true"
ENABLE_PUBLIC_REGISTRATION=os.environ.get("ENABLE_PUBLIC_REGISTRATION","False").lower()=="true"
INSTALLED_APPS=["django.contrib.admin","django.contrib.auth","django.contrib.contenttypes","django.contrib.sessions","django.contrib.messages","django.contrib.staticfiles","accounts.apps.AccountsConfig","core","offices","schools","content","issuances","services","appointments","tickets","feedback","vacancies","events","verification","notifications","audit"]
MIDDLEWARE=["django.middleware.security.SecurityMiddleware","whitenoise.middleware.WhiteNoiseMiddleware","django.contrib.sessions.middleware.SessionMiddleware","django.middleware.common.CommonMiddleware","core.middleware.OnlineTransactionsDisabledMiddleware","django.middleware.csrf.CsrfViewMiddleware","django.contrib.auth.middleware.AuthenticationMiddleware","core.middleware.MaintenanceModeMiddleware","django.contrib.messages.middleware.MessageMiddleware","django.middleware.clickjacking.XFrameOptionsMiddleware","core.middleware.SecurityHeadersMiddleware"]
ROOT_URLCONF="config.urls"
TEMPLATES=[{"BACKEND":"django.template.backends.django.DjangoTemplates","DIRS":[BASE_DIR/"templates"],"APP_DIRS":True,"OPTIONS":{"context_processors":["django.template.context_processors.request","django.contrib.auth.context_processors.auth","django.contrib.messages.context_processors.messages","core.context_processors.portal_settings"]}}]
WSGI_APPLICATION="config.wsgi.application"
u=urlparse(os.environ.get("DATABASE_URL",""))
DATABASES={"default":{"ENGINE":"django.db.backends.postgresql","NAME":u.path.lstrip("/"),"USER":u.username,"PASSWORD":u.password,"HOST":u.hostname,"PORT":u.port or 5432}} if u.scheme else {"default":{"ENGINE":"django.db.backends.sqlite3","NAME":BASE_DIR/"db.sqlite3"}}
AUTH_USER_MODEL="accounts.User"
AUTHENTICATION_BACKENDS=["accounts.backends.UsernameOrEmailBackend"]
LANGUAGE_CODE="en-us"; TIME_ZONE="Asia/Manila"; USE_I18N=True; USE_TZ=True
STATIC_URL="/static/"; STATIC_ROOT=BASE_DIR/"staticfiles"; STATICFILES_DIRS=[BASE_DIR/"static", BASE_DIR/"imageload"]
STORAGES={"default":{"BACKEND":"django.core.files.storage.FileSystemStorage"},"staticfiles":{"BACKEND":"whitenoise.storage.CompressedManifestStaticFilesStorage" if not DEBUG else "django.contrib.staticfiles.storage.StaticFilesStorage"}}
MEDIA_URL="/media/"; MEDIA_ROOT=BASE_DIR/"media"
DEFAULT_AUTO_FIELD="django.db.models.BigAutoField"
LOGIN_URL="accounts:login"; LOGIN_REDIRECT_URL="core:dashboard"; LOGOUT_REDIRECT_URL="core:home"
AUTH_PASSWORD_VALIDATORS=[{"NAME":"django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},{"NAME":"django.contrib.auth.password_validation.MinimumLengthValidator","OPTIONS":{"min_length":12}},{"NAME":"django.contrib.auth.password_validation.CommonPasswordValidator"},{"NAME":"django.contrib.auth.password_validation.NumericPasswordValidator"}]
SESSION_COOKIE_HTTPONLY=True; SESSION_COOKIE_SAMESITE="Lax"; CSRF_COOKIE_SAMESITE="Lax"; SESSION_COOKIE_AGE=3600
SECURE_SSL_REDIRECT=os.environ.get("DJANGO_SECURE_SSL_REDIRECT",str(not DEBUG)).lower()=="true"; SESSION_COOKIE_SECURE=CSRF_COOKIE_SECURE=not DEBUG
SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO","https")
SECURE_HSTS_SECONDS=31536000 if not DEBUG else 0; SECURE_HSTS_INCLUDE_SUBDOMAINS=not DEBUG; SECURE_HSTS_PRELOAD=not DEBUG; SECURE_CONTENT_TYPE_NOSNIFF=True; X_FRAME_OPTIONS="DENY"; FILE_UPLOAD_MAX_MEMORY_SIZE=10*1024*1024
EMAIL_BACKEND=os.environ.get("EMAIL_BACKEND","django.core.mail.backends.console.EmailBackend")
EMAIL_HOST=os.environ.get("EMAIL_HOST","")
EMAIL_PORT=int(os.environ.get("EMAIL_PORT","587"))
EMAIL_HOST_USER=os.environ.get("EMAIL_HOST_USER","")
EMAIL_HOST_PASSWORD=os.environ.get("EMAIL_HOST_PASSWORD","")
EMAIL_USE_TLS=os.environ.get("EMAIL_USE_TLS","True").lower()=="true"
EMAIL_TIMEOUT=int(os.environ.get("EMAIL_TIMEOUT","10"))
DEFAULT_FROM_EMAIL=os.environ.get("DEFAULT_FROM_EMAIL","SDO Sulu Portal <noreply@localhost>")
SERVER_EMAIL=DEFAULT_FROM_EMAIL
ADMINS=[("SDO Sulu Administrator",email.strip()) for email in os.environ.get("ADMIN_EMAILS","").split(",") if email.strip()]
FACEBOOK_PAGE_ID=os.environ.get("FACEBOOK_PAGE_ID","100042494841401")
FACEBOOK_PAGE_URL=os.environ.get("FACEBOOK_PAGE_URL","https://www.facebook.com/profile.php?id=100042494841401")
FACEBOOK_PAGE_ACCESS_TOKEN=os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN","")
FACEBOOK_GRAPH_API_VERSION=os.environ.get("FACEBOOK_GRAPH_API_VERSION","v23.0")
FACEBOOK_SYNC_AUTHOR=os.environ.get("FACEBOOK_SYNC_AUTHOR","")
CSRF_TRUSTED_ORIGINS=[item.strip() for item in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS","").split(",") if item.strip()]
if RAILWAY_PUBLIC_DOMAIN:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RAILWAY_PUBLIC_DOMAIN}")
LOGGING={"version":1,"disable_existing_loggers":False,"formatters":{"standard":{"format":"{asctime} {levelname} {name} {message}","style":"{"}},"handlers":{"console":{"class":"logging.StreamHandler","formatter":"standard"},"mail_admins":{"class":"django.utils.log.AdminEmailHandler","level":"ERROR","include_html":False}},"root":{"handlers":["console"],"level":os.environ.get("LOG_LEVEL","INFO")},"loggers":{"django.request":{"handlers":["console","mail_admins"],"level":"ERROR","propagate":False},"django.security":{"handlers":["console","mail_admins"],"level":"WARNING","propagate":False}}}
