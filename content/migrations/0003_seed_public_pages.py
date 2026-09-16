from django.db import migrations


PAGES = [
    ("about", "About SDO Sulu", "Official information about the Schools Division Office of Sulu.", "The Schools Division Office of Sulu supports the delivery of accessible, inclusive, and quality basic education across the division. This page is maintained by authorized SDO personnel through the portal's System Administration interface."),
    ("mission", "Mission", "The division's commitment to learners and education stakeholders.", "SDO Sulu works with schools, families, communities, and partners to support learner development, strengthen education services, and uphold the mandate and standards of the Department of Education."),
    ("vision", "Vision", "The future SDO Sulu works to help build.", "SDO Sulu seeks a responsive and inclusive education system where every learner is supported by capable personnel, well-governed schools, and engaged communities."),
    ("core-values", "Core Values", "Values that guide public service and education.", "Maka-Diyos\nMaka-tao\nMakakalikasan\nMakabansa"),
    ("officials", "Division Officials", "Official leadership information for SDO Sulu.", "The division maintains its official leadership directory through this portal. Authorized administrators may publish current names, positions, and office contact information on this page."),
    ("organizational-structure", "Organizational Structure", "How offices and sections work together across the division.", "The Schools Division Office is organized into leadership offices, curriculum implementation functions, school governance and operations functions, and administrative support services. The current organizational chart may be uploaded and maintained by an authorized administrator."),
    ("privacy-policy", "Privacy Policy", "How this portal handles personal information.", "SDO Sulu processes personal information only for authorized public-service and administrative purposes. Access is limited according to assigned roles, sensitive submissions are not published, and system activities are recorded for security and accountability. Questions about personal information may be directed to the official contact details shown on this portal."),
    ("terms-of-use", "Terms of Use", "Conditions for using the official SDO Sulu portal.", "Information published on this portal is provided for official public reference. Users must not misuse the portal, attempt unauthorized access, upload harmful files, or misrepresent published records. Official issuances should be confirmed using their reference details and the document-verification service when available."),
]


def seed_pages(apps, schema_editor):
    PublicPage = apps.get_model("content", "PublicPage")
    for slug, title, summary, body in PAGES:
        PublicPage.objects.get_or_create(
            slug=slug,
            defaults={"title": title, "summary": summary, "body": body, "published": True},
        )


def unseed_pages(apps, schema_editor):
    PublicPage = apps.get_model("content", "PublicPage")
    PublicPage.objects.filter(slug__in=[page[0] for page in PAGES]).delete()


class Migration(migrations.Migration):
    dependencies = [("content", "0002_publicpage_announcement_office_download_office_and_more")]
    operations = [migrations.RunPython(seed_pages, unseed_pages)]
