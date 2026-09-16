import re

from django.db import OperationalError, ProgrammingError

from content.models import SiteSetting


DEFAULTS = {
    "SDO_NAME": "Schools Division Office of Sulu",
    "ADDRESS": "Scott Road, San Raymundo, Jolo, Sulu",
    "EMAIL": "sdskiram.irilis@deped.gov.ph",
    "PHONE": "0965 754 5663",
    "WHATSAPP": "+63 966 175 6976",
    "MAP_URL": "https://www.google.com/maps/place/Department+of+Education/@6.0516351,121.0015126,20z/data=!4m6!3m5!1s0x3244fdcd27283039:0x17e97c0b5fafcf44!8m2!3d6.0516996!4d121.0017765!16s%2Fg%2F1txx_v9q?entry=ttu&g_ep=EgoyMDI2MDkxMy4wIKXMDSoASAFQAw%3D%3D",
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
