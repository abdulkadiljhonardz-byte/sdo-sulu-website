from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from issuances.models import Issuance


MEMOS = [
    ("DM 01, s. 2026", "Division-Wide Orientation on the Administration of Computer-Based National Career Assessment Examination", "https://www.facebook.com/100042494841401/posts/1740823037344174/"),
    ("DM 02, s. 2026", "Immediate Collection and Distribution of Textbooks", "https://www.facebook.com/100042494841401/posts/1741574150602396/"),
    ("DM 03, s. 2026", "Notice of Meeting", "https://www.facebook.com/100042494841401/posts/1747411886685289/"),
    ("DM 06, s. 2026", "Learners Government Election (SELG and SSLG) for SY 2026–2027", "https://www.facebook.com/100042494841401/posts/1755360949223716/"),
    ("DM 08, s. 2026", "Notice of Meeting", "https://www.facebook.com/100042494841401/posts/1758778025548675/"),
    ("DM 09, s. 2026", "Postponement of the First Sulu Association of Education Leaders", "https://www.facebook.com/100042494841401/posts/1758788182214326/"),
    ("DM 14, s. 2026", "No Collection Policy", "https://www.facebook.com/100042494841401/photos/division-memo-no-14-s-2026no-collection-policy/1765353534891124/"),
    ("DM 14, s. 2026 [alternate post]", "Graduation and Moving Up Exercises", "https://www.facebook.com/100042494841401/posts/1769169134509564/"),
    ("DM 15, s. 2026", "Conduct of Rapid Mathematics Assessment (RMA) Post-Test", "https://www.facebook.com/100042494841401/posts/1769376694488808/"),
    ("DM 16, s. 2026", "Notice of Meeting re: 2026 Regional Schools Press Conference", "https://www.facebook.com/100042494841401/photos/division-memo-no-16-s-2026notice-of-meeting-re-2026-regional-schools-press-confe/1773001967459614/"),
    ("DM 22, s. 2026", "Submission of School Best Practices in Arts and Culture", ""),
    ("DM 23, s. 2026", "Submission of School Site Ownership", ""),
    ("DM 24, s. 2026", "Division Memo No. 24", "https://www.facebook.com/100042494841401/posts/1786216749471469/"),
    ("DM 26, s. 2026", "2026 National Women's Month Celebration", "https://www.facebook.com/100042494841401/posts/1788497259243418/"),
    ("DM 27, s. 2026", "2026 Division Festival of Talents", "https://www.facebook.com/100042494841401/posts/1789534222473055/"),
    ("DM 30, s. 2026", "Mandatory Compliance with DM-OUTHROD-2026-0095 on Renewal/Hiring of School-Based Administrative Support Staff", ""),
    ("DM 32, s. 2026", "Notice of Vacancy", ""),
    ("DM 34, s. 2026", "Division Memo No. 34", "https://www.facebook.com/100042494841401/posts/1842015490558261/"),
    ("DM 39, s. 2026", "Issuance of Provisional Permit to Operate for Strengthened Senior High School Program", "https://www.facebook.com/100042494841401/photos/1855680319191778/"),
    ("DM 42, s. 2026", "Change of Schedule on the Division-Led Training of Teachers on the Revised K–10", "https://www.facebook.com/100042494841401/photos/1857795525646924/"),
    ("DM 44, s. 2026", "Submission of Identified Learner Beneficiaries for the TUPAD Program", "https://www.facebook.com/100042494841401/posts/1872902674136209/"),
    ("DM 46, s. 2026", "Urgent Submission of Lists of Sulu EPP/TLE/TVL/Tech-Pro Teachers", "https://www.facebook.com/100042494841401/photos/division-memo-no-46-s-2026urgent-submission-of-lists-of-sulu-epptletvltech-pro-t/1880856740007469/"),
    ("DM 50, s. 2026", "Division Memo No. 50", "https://www.facebook.com/100042494841401/posts/1896710705088739/"),
    ("DM 54, s. 2026", "Recruitment and Selection Process of Teacher I for Kindergarten, Elementary, JHS and SHS", ""),
    ("DM 61, s. 2026", "Notice of Meeting re: Regional Office Schools Visitation and Meeting of Public Schools District Supervisors", "https://www.facebook.com/100042494841401/photos/1802205757872568/"),
    ("DM 63, s. 2026", "Implementation Guidelines for DepEd Order No. 016, s. 2026 (ILAW Lesson Planning and Learning Design)", "https://www.facebook.com/100042494841401/photos/1950883659671443/"),
    ("DM 68, s. 2026", "Strict Adherence to DepEd Order No. 009, s. 2026 (Three-Term Calendar) and Clarification on Academic Honors", "https://www.facebook.com/100042494841401/posts/1880858450007298/"),
    ("DM 69, s. 2026", "Meeting on the Conduct of the Computer-Based Assessment", "https://www.facebook.com/100042494841401/posts/1962666851826457/"),
    ("DM 71, s. 2026", "Participation in the 126th Philippine Civil Service Anniversary (PCSA) Celebration", "https://www.facebook.com/100042494841401/posts/1962905848469224/"),
    ("DM 72, s. 2026", "Revised Schedule for the Regional Monitoring and Evaluation of School Class Program, Teachers' Loads and Class Size", "https://www.facebook.com/100042494841401/posts/1966453428114466/"),
    ("DM 73, s. 2026", "Call for Submission of Basic Research and Action Research Proposals", "https://www.facebook.com/100042494841401/posts/1967583231334819/"),
    ("DM 74, s. 2026", "2026 National Teachers' Month, National Teachers' Day, and World Teachers' Day Celebrations", "https://www.facebook.com/100042494841401/posts/1967594004667075/"),
]


class Command(BaseCommand):
    help = "Import the supplied 2026 SDO Sulu Facebook memorandum index."

    @transaction.atomic
    def handle(self, *args, **options):
        creator = User.objects.filter(is_superuser=True).order_by("pk").first()
        created = 0
        skipped = 0
        for reference, title, source_url in MEMOS:
            _, was_created = Issuance.objects.get_or_create(
                reference_number=reference,
                defaults={
                    "title": title,
                    "category": Issuance.Category.DIVISION_MEMO,
                    "year": 2026,
                    "date_issued": None,
                    "description": "",
                    "source_url": source_url,
                    "status": "PUBLISHED",
                    "keywords": "2026 division memorandum Facebook official post",
                    "created_by": creator,
                },
            )
            created += int(was_created)
            skipped += int(not was_created)
        self.stdout.write(
            self.style.SUCCESS(
                f"Memorandum import complete: {created} created, {skipped} already existed."
            )
        )
