import re

from django.db import OperationalError, ProgrammingError

from content.models import SiteSetting


DEFAULTS = {
    "SDO_NAME": "Schools Division Office of Sulu",
    "ADDRESS": "Scott Road, San Raymundo, Jolo, Sulu",
    "EMAIL": "sdskiram.irilis@deped.gov.ph",
    "PHONE": "0965 754 5663",
    "WHATSAPP": "+63 966 175 6976",
    "OFFICE_HOURS": "Monday–Friday, 8:00 AM–5:00 PM",
    "HOMEPAGE_BANNER": "",
    "FOOTER_TEXT": "Official Digital Information Portal",
    "MAINTENANCE_MODE": "False",
}


def portal_settings(request):
    values = DEFAULTS.copy()
    try:
        values.update(dict(SiteSetting.objects.filter(key__in=values).values_list("key", "value")))
    except (OperationalError, ProgrammingError):
        pass
    phone_digits = re.sub(r"\D", "", values["PHONE"])
    whatsapp_digits = re.sub(r"\D", "", values["WHATSAPP"])
    if phone_digits.startswith("0"):
        phone_digits = "63" + phone_digits[1:]
    if whatsapp_digits.startswith("0"):
        whatsapp_digits = "63" + whatsapp_digits[1:]
    values["PHONE_URI"] = f"+{phone_digits}" if phone_digits else ""
    values["WHATSAPP_URI"] = (
        f"https://wa.me/{whatsapp_digits}" if whatsapp_digits else ""
    )
    return {"PORTAL_NAME": values["SDO_NAME"], "PORTAL_SETTINGS": values}
