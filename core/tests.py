from datetime import date, timedelta
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from django.utils import timezone
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from accounts.models import Role, StaffProfile, User
from accounts.roles import synchronize_role_permissions
from audit.models import AuditLog
from content.models import News, PublicPage, SiteSetting
from content.facebook_import import ImportedFacebookPost
from content.facebook_page_sync import is_memorandum, sync_facebook_news
from core.models import AnalyticsEvent
from issuances.models import Issuance, IssuanceVersion
from offices.models import District, Office
from schools.models import School


class InformationPortalModeTests(TestCase):
    def test_transactional_routes_are_not_publicly_accessible(self):
        for route_name in (
            "services:submit",
            "appointments:index",
            "tickets:index",
        ):
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 404)

    def test_home_does_not_advertise_transactional_services(self):
        response = self.client.get(reverse("core:home"))
        self.assertNotContains(response, "Online Services")
        self.assertNotContains(response, "Help Desk")
        self.assertContains(response, "Public information")

    @override_settings(ENABLE_ONLINE_TRANSACTIONS=True)
    def test_feature_gate_can_be_enabled_explicitly(self):
        response = self.client.get(reverse("services:track"))
        self.assertEqual(response.status_code, 200)


class ContentManagementTests(TestCase):
    @staticmethod
    def _png_bytes():
        output = BytesIO()
        Image.new("RGB", (32, 32), "green").save(output, format="PNG")
        return output.getvalue()

    def test_regular_user_cannot_open_content_management(self):
        user = User.objects.create_user("visitor", password="StrongPass!234")
        self.client.force_login(user)
        response = self.client.get(reverse("core:content_management"))
        self.assertEqual(response.status_code, 403)

    def test_sdo_administrator_can_publish_news(self):
        user = User.objects.create_user(
            "portaladmin",
            email="portaladmin@example.com",
            password="StrongPass!234",
            role=Role.ADMIN,
            is_staff=True,
        )
        self.client.force_login(user)
        response = self.client.post(
            reverse("core:content_create", args=["news"]),
            {
                "title": "Official division news",
                "body": "Classes and offices will follow the published schedule.",
                "category": "Advisory",
                "is_published": "on",
                "is_featured": "on",
            },
        )
        self.assertRedirects(
            response, reverse("core:content_list", args=["news"])
        )
        news = News.objects.get()
        self.assertEqual(news.author, user)
        self.assertTrue(news.is_published)
        self.assertTrue(news.slug)

    def test_news_management_form_accepts_a_cover_photo(self):
        user = User.objects.create_user(
            "newsadmin",
            password="StrongPass!234",
            role=Role.ADMIN,
            is_staff=True,
        )
        self.client.force_login(user)
        response = self.client.post(
            reverse("core:content_create", args=["news"]),
            {
                "title": "News with a photo",
                "body": "Complete public news caption.",
                "category": "Division News",
                "cover_image": SimpleUploadedFile(
                    "news.png", self._png_bytes(), content_type="image/png"
                ),
            },
        )
        self.assertRedirects(
            response, reverse("core:content_list", args=["news"])
        )
        self.assertTrue(News.objects.get().cover_image.name.endswith(".png"))

    @patch("core.management_views.import_facebook_post")
    def test_admin_facebook_import_can_publish_caption_and_photo(self, importer):
        admin = User.objects.create_user(
            "facebookadmin",
            password="StrongPass!234",
            role=Role.ADMIN,
            is_staff=True,
        )
        importer.return_value = ImportedFacebookPost(
            url="https://www.facebook.com/sdosulu/posts/123456",
            title="SDO Sulu official update",
            caption="This is the complete caption returned by the public post.",
            image_bytes=self._png_bytes(),
            image_name="facebook-cover.png",
            image_content_type="image/png",
        )
        self.client.force_login(admin)
        response = self.client.post(
            reverse("core:facebook_import", args=["news"]),
            {
                "facebook_url": "https://www.facebook.com/sdosulu/posts/123456",
                "publish_now": "on",
            },
        )
        item = News.objects.get()
        self.assertRedirects(
            response, reverse("core:content_update", args=["news", item.pk])
        )
        self.assertTrue(item.is_published)
        self.assertIsNotNone(item.published_at)
        self.assertEqual(item.author, admin)
        self.assertEqual(item.body, importer.return_value.caption)
        self.assertEqual(item.source_url, importer.return_value.url)
        self.assertIsNotNone(item.source_imported_at)
        self.assertTrue(item.cover_image.name.endswith(".png"))

    def test_facebook_import_rejects_non_facebook_links(self):
        admin = User.objects.create_user(
            "safeimportadmin",
            password="StrongPass!234",
            role=Role.ADMIN,
            is_staff=True,
        )
        self.client.force_login(admin)
        response = self.client.post(
            reverse("core:facebook_import", args=["news"]),
            {"facebook_url": "https://example.com/internal-photo"},
        )
        self.assertRedirects(response, reverse("core:content_create", args=["news"]))
        self.assertFalse(News.objects.exists())

    @patch("content.facebook_page_sync.download_facebook_image")
    @patch("content.facebook_page_sync._fetch_posts")
    def test_official_page_sync_imports_news_and_excludes_memos(
        self, fetch_posts, download_image
    ):
        fetch_posts.return_value = [
            {
                "id": "100042494841401_news1",
                "message": "SDO Sulu learners join the regional education summit.",
                "created_time": "2026-09-17T08:00:00+0000",
                "permalink_url": "https://www.facebook.com/sdosulu/posts/news1",
                "full_picture": "https://scontent.xx.fbcdn.net/news1.png",
            },
            {
                "id": "100042494841401_memo1",
                "message": "Division Memorandum No. 100, s. 2026",
                "created_time": "2026-09-17T09:00:00+0000",
                "permalink_url": "https://www.facebook.com/sdosulu/posts/memo1",
                "full_picture": "https://scontent.xx.fbcdn.net/memo1.png",
            },
            {
                "id": "100042494841401_old1",
                "message": "Old page news",
                "created_time": "2025-12-31T09:00:00+0000",
                "permalink_url": "https://www.facebook.com/sdosulu/posts/old1",
                "full_picture": "https://scontent.xx.fbcdn.net/old1.png",
            },
        ]
        download_image.return_value = (
            self._png_bytes(),
            "facebook-cover.png",
            "image/png",
        )
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            summary = sync_facebook_news()
            self.assertEqual(summary.imported, 1)
            self.assertEqual(summary.excluded_memos, 1)
            self.assertEqual(summary.outside_date_range, 1)
            item = News.objects.get(facebook_post_id="100042494841401_news1")
            self.assertTrue(item.is_published)
            self.assertEqual(item.category, "Facebook News")
            self.assertIn("regional education summit", item.body)

    def test_facebook_memo_filter_recognizes_official_memo_labels(self):
        self.assertTrue(is_memorandum("DM No. 88, s. 2026"))
        self.assertTrue(is_memorandum("Office Memorandum for all personnel"))
        self.assertFalse(is_memorandum("Division athletes win regional meet"))

    def test_published_news_appears_on_homepage(self):
        news = News.objects.create(
            title="Public division news",
            slug="public-division-news",
            body="Full news content.",
            is_published=True,
            published_at=timezone.now(),
            source_url="https://www.facebook.com/sdosulu/posts/99",
        )
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, news.title)
        self.assertContains(response, reverse("content:news_detail", args=[news.slug]))

    def test_system_admin_pages_render_inside_portal(self):
        user = User.objects.create_user(
            "systemadmin",
            email="systemadmin@example.com",
            password="StrongPass!234",
            role=Role.ADMIN,
            is_staff=True,
        )
        self.client.force_login(user)
        routes = (
            "core:content_management",
            "core:analytics_dashboard",
            "core:data_workspace",
            "core:facebook_news_sync",
            "core:reports",
            "core:portal_settings",
            "core:feedback_management",
            "core:notification_management",
            "core:audit_management",
            "core:legacy_records",
        )
        for route_name in routes:
            with self.subTest(route_name=route_name):
                self.assertEqual(self.client.get(reverse(route_name)).status_code, 200)

    def test_portal_settings_update_public_identity(self):
        user = User.objects.create_user(
            "settingsadmin",
            password="StrongPass!234",
            role=Role.ADMIN,
            is_staff=True,
        )
        self.client.force_login(user)
        response = self.client.post(
            reverse("core:portal_settings"),
            {
                "sdo_name": "SDO Sulu Test",
                "address": "Test Address, Sulu",
                "email": "portal@example.com",
                "phone": "123-4567",
                "office_hours": "Weekdays",
                "homepage_banner": "Test public notice",
                "footer_text": "Official Test Portal",
            },
        )
        self.assertRedirects(response, reverse("core:portal_settings"))
        public_home = self.client.get(reverse("core:home"))
        self.assertContains(public_home, "Test Address, Sulu")
        self.assertContains(public_home, "Test public notice")

    def test_maintenance_mode_blocks_public_pages_but_keeps_staff_login(self):
        SiteSetting.objects.create(key="MAINTENANCE_MODE", value="True")
        self.assertEqual(self.client.get(reverse("core:home")).status_code, 503)
        self.assertEqual(self.client.get(reverse("accounts:login")).status_code, 200)

    def test_office_staff_is_limited_to_assigned_office_and_draft_content(self):
        records = Office.objects.create(name="Records Section", code="records-section")
        hr = Office.objects.create(name="Human Resources", code="human-resources")
        staff = User.objects.create_user(
            "recordsstaff",
            email="records@example.com",
            password="StrongPass!234",
            role=Role.STAFF,
        )
        StaffProfile.objects.create(user=staff, office=records, position="Records Officer")
        synchronize_role_permissions(staff)
        News.objects.create(
            title="HR-only record",
            slug="hr-only-record",
            body="Restricted",
            office=hr,
            is_published=False,
        )
        self.client.force_login(staff)
        response = self.client.post(
            reverse("core:content_create", args=["news"]),
            {
                "title": "Records update",
                "body": "Records section information",
                "category": "Office News",
                "office": hr.pk,
                "is_published": "on",
            },
        )
        self.assertRedirects(response, reverse("core:content_list", args=["news"]))
        created = News.objects.get(slug="records-update")
        self.assertEqual(created.office, records)
        self.assertFalse(created.is_published)
        listing = self.client.get(reverse("core:content_list", args=["news"]))
        self.assertContains(listing, "Records update")
        self.assertNotContains(listing, "HR-only record")

    def test_replacing_issuance_pdf_preserves_previous_version(self):
        office = Office.objects.create(name="Legal Office", code="legal-office")
        admin = User.objects.create_user(
            "documentadmin",
            email="documentadmin@example.com",
            password="StrongPass!234",
            role=Role.ADMIN,
            is_staff=True,
        )
        issuance = Issuance.objects.create(
            category=Issuance.Category.DIVISION_MEMO,
            reference_number="DM-2026-001",
            title="Original memorandum",
            year=2026,
            date_issued=date(2026, 9, 16),
            office=office,
            pdf=SimpleUploadedFile("original.pdf", b"%PDF-1.4 original", content_type="application/pdf"),
            status="PUBLISHED",
            created_by=admin,
        )
        old_name = issuance.pdf.name
        self.client.force_login(admin)
        response = self.client.post(
            reverse("core:content_update", args=["issuances", issuance.pk]),
            {
                "category": Issuance.Category.DIVISION_MEMO,
                "reference_number": issuance.reference_number,
                "title": "Revised memorandum",
                "description": "Corrected attachment",
                "year": 2026,
                "date_issued": "2026-09-16",
                "office": office.pk,
                "status": "PUBLISHED",
                "keywords": "memo",
                "revision_reason": "Corrected the signed attachment.",
                "pdf": SimpleUploadedFile("revised.pdf", b"%PDF-1.4 revised", content_type="application/pdf"),
            },
        )
        self.assertRedirects(response, reverse("core:content_list", args=["issuances"]))
        version = IssuanceVersion.objects.get(issuance=issuance)
        self.assertEqual(version.file.name, old_name)
        self.assertEqual(version.reason, "Corrected the signed attachment.")
        issuance.refresh_from_db()
        self.assertNotEqual(issuance.pdf.name, old_name)

    def test_new_memorandum_uses_cover_image_and_pdf_without_body(self):
        office = Office.objects.create(name="Records Office", code="records")
        admin = User.objects.create_user(
            "memoimageadmin",
            password="StrongPass!234",
            role=Role.ADMIN,
            is_staff=True,
        )
        self.client.force_login(admin)
        response = self.client.post(
            reverse("core:content_create", args=["issuances"]),
            {
                "category": Issuance.Category.DIVISION_MEMO,
                "reference_number": "DM-2026-IMAGE",
                "title": "Memorandum with official cover",
                "year": 2026,
                "date_issued": "2026-09-17",
                "office": office.pk,
                "cover_image": SimpleUploadedFile(
                    "memo-cover.png", self._png_bytes(), content_type="image/png"
                ),
                "pdf": SimpleUploadedFile(
                    "memo.pdf", b"%PDF-1.4 memo", content_type="application/pdf"
                ),
                "status": "PUBLISHED",
            },
        )
        self.assertRedirects(
            response, reverse("core:content_list", args=["issuances"])
        )
        item = Issuance.objects.get(reference_number="DM-2026-IMAGE")
        self.assertEqual(item.description, "")
        self.assertTrue(item.cover_image.name.endswith(".png"))
        home = self.client.get(reverse("core:home"))
        self.assertContains(home, item.cover_image.url)
        detail = self.client.get(reverse("issuances:detail", args=[item.pk]))
        self.assertContains(detail, "Download PDF")

    def test_seeded_public_information_page_is_available(self):
        page = PublicPage.objects.get(slug="about")
        response = self.client.get(reverse("pages:detail", args=[page.slug]))
        self.assertEqual(response.status_code, 200)

        contact = PublicPage.objects.get(slug="contact")
        response = self.client.get(reverse("pages:detail", args=[contact.slug]))
        self.assertContains(response, "sdskiram.irilis@deped.gov.ph")
        self.assertContains(response, "0965 754 5663")
        self.assertContains(response, "+63 966 175 6976")
        self.assertContains(response, "https://wa.me/639661756976")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_author_receives_email_when_news_is_published(self):
        office = Office.objects.create(name="ICT Unit", code="ict-unit")
        author = User.objects.create_user(
            "ictstaff", email="ictstaff@example.com", password="StrongPass!234", role=Role.STAFF
        )
        StaffProfile.objects.create(user=author, office=office, position="ICT Officer")
        item = News.objects.create(
            title="Draft ICT update",
            slug="draft-ict-update",
            body="Draft information",
            office=office,
            author=author,
            is_published=False,
        )
        admin = User.objects.create_user(
            "publishingadmin", password="StrongPass!234", role=Role.ADMIN, is_staff=True
        )
        self.client.force_login(admin)
        response = self.client.post(
            reverse("core:content_update", args=["news", item.pk]),
            {
                "title": item.title,
                "body": item.body,
                "category": "ICT",
                "office": office.pk,
                "is_published": "on",
            },
        )
        self.assertRedirects(response, reverse("core:content_list", args=["news"]))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("published", mail.outbox[0].subject.lower())
        self.assertEqual(mail.outbox[0].to, [author.email])

    def test_scheduled_and_expired_news_are_not_public(self):
        News.objects.create(title="Future news", slug="future-news", body="Later", is_published=True, published_at=timezone.now() + timedelta(days=1))
        News.objects.create(title="Expired news", slug="expired-news", body="Old", is_published=True, published_at=timezone.now() - timedelta(days=2), expires_at=timezone.now() - timedelta(days=1))
        response = self.client.get(reverse("content:news"))
        self.assertNotContains(response, "Future news")
        self.assertNotContains(response, "Expired news")

    def test_archive_requires_confirmation_and_removes_publication(self):
        admin = User.objects.create_user("archiveadmin", password="StrongPass!234", role=Role.ADMIN, is_staff=True)
        item = News.objects.create(title="Archive me", slug="archive-me", body="Notice", is_published=True)
        self.client.force_login(admin)
        url = reverse("core:content_archive", args=["news", item.pk])
        self.assertEqual(self.client.post(url).status_code, 403)
        self.assertEqual(self.client.post(url, {"confirm": "ARCHIVE"}).status_code, 302)
        item.refresh_from_db()
        self.assertTrue(item.archived)
        self.assertFalse(item.is_published)

    def test_admin_can_permanently_delete_news_and_uploaded_picture(self):
        admin = User.objects.create_user(
            "deletenewsadmin",
            password="StrongPass!234",
            role=Role.ADMIN,
            is_staff=True,
        )
        self.client.force_login(admin)
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            item = News.objects.create(
                title="Delete this news",
                slug="delete-this-news",
                body="Temporary news",
                cover_image=SimpleUploadedFile(
                    "delete-news.png", self._png_bytes(), content_type="image/png"
                ),
            )
            item_id = item.pk
            storage, image_name = item.cover_image.storage, item.cover_image.name
            url = reverse("core:content_delete", args=["news", item_id])
            self.assertEqual(self.client.post(url).status_code, 403)
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(url, {"confirm": "DELETE"})
            self.assertRedirects(response, reverse("core:content_list", args=["news"]))
            self.assertFalse(News.objects.filter(pk=item_id).exists())
            self.assertFalse(storage.exists(image_name))
            self.assertTrue(
                AuditLog.objects.filter(
                    action="News Article permanently deleted",
                    object_id=str(item_id),
                ).exists()
            )

    def test_admin_can_permanently_delete_memo_and_all_files(self):
        office = Office.objects.create(name="Delete Test Office", code="delete-test")
        admin = User.objects.create_user(
            "deletememoadmin",
            password="StrongPass!234",
            role=Role.ADMIN,
            is_staff=True,
        )
        self.client.force_login(admin)
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            item = Issuance.objects.create(
                category=Issuance.Category.DIVISION_MEMO,
                reference_number="DM-DELETE-001",
                title="Delete this memorandum",
                year=2026,
                date_issued=date(2026, 9, 17),
                office=office,
                cover_image=SimpleUploadedFile(
                    "delete-memo.png", self._png_bytes(), content_type="image/png"
                ),
                pdf=SimpleUploadedFile(
                    "delete-memo.pdf", b"%PDF-1.4 current", content_type="application/pdf"
                ),
            )
            version = IssuanceVersion.objects.create(
                issuance=item,
                version_number=1,
                file=SimpleUploadedFile(
                    "old-memo.pdf", b"%PDF-1.4 old", content_type="application/pdf"
                ),
                reason="Old version",
                uploaded_by=admin,
            )
            item_id = item.pk
            files = [
                (item.cover_image.storage, item.cover_image.name),
                (item.pdf.storage, item.pdf.name),
                (version.file.storage, version.file.name),
            ]
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    reverse("core:content_delete", args=["issuances", item_id]),
                    {"confirm": "DELETE"},
                )
            self.assertRedirects(
                response, reverse("core:content_list", args=["issuances"])
            )
            self.assertFalse(Issuance.objects.filter(pk=item_id).exists())
            self.assertFalse(IssuanceVersion.objects.filter(pk=version.pk).exists())
            for storage, name in files:
                self.assertFalse(storage.exists(name))
            self.assertTrue(
                AuditLog.objects.filter(
                    action="Issuance permanently deleted",
                    object_id=str(item_id),
                ).exists()
            )

    def test_office_staff_cannot_permanently_delete_news(self):
        office = Office.objects.create(name="No Delete Office", code="no-delete")
        staff = User.objects.create_user(
            "nodeletestaff",
            password="StrongPass!234",
            role=Role.STAFF,
        )
        StaffProfile.objects.create(user=staff, office=office, position="Encoder")
        synchronize_role_permissions(staff)
        item = News.objects.create(
            title="Protected news", slug="protected-news", body="Keep this", office=office
        )
        self.client.force_login(staff)
        response = self.client.post(
            reverse("core:content_delete", args=["news", item.pk]),
            {"confirm": "DELETE"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(News.objects.filter(pk=item.pk).exists())

    def test_usage_events_feed_analytics(self):
        district = District.objects.create(name="Jolo District", municipality="Jolo")
        School.objects.create(school_id="100001", name="Test School", district=district, classification="PUBLIC")
        self.client.get(reverse("core:search"), {"q": "school"})
        self.client.get(reverse("schools:directory"))
        self.assertEqual(AnalyticsEvent.objects.filter(event_type=AnalyticsEvent.Type.SEARCH).count(), 1)
        self.assertEqual(AnalyticsEvent.objects.filter(event_type=AnalyticsEvent.Type.DIRECTORY_VISIT).count(), 1)

    def test_school_csv_import_and_report_exports(self):
        District.objects.create(name="Sulu Central", municipality="Jolo")
        admin = User.objects.create_user("dataadmin", password="StrongPass!234", role=Role.ADMIN, is_staff=True)
        self.client.force_login(admin)
        csv_file = SimpleUploadedFile(
            "schools.csv",
            b"school_id,name,district,classification,municipality\n123456,Sulu Test School,Sulu Central,PUBLIC,Jolo\n",
            content_type="text/csv",
        )
        response = self.client.post(reverse("core:data_workspace"), {"dataset": "schools", "spreadsheet": csv_file})
        self.assertRedirects(response, reverse("core:data_workspace"))
        self.assertTrue(School.objects.filter(school_id="123456").exists())
        csv_response = self.client.get(reverse("core:export_data", args=["schools", "csv"]))
        self.assertEqual(csv_response.status_code, 200)
        self.assertIn(b"123456", csv_response.content)
        pdf_response = self.client.get(reverse("core:export_data", args=["schools", "pdf"]))
        self.assertEqual(pdf_response.status_code, 200)
        self.assertTrue(pdf_response.content.startswith(b"%PDF-1.4"))

    def test_health_endpoint_checks_database(self):
        response = self.client.get(reverse("core:health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["database"], "ok")

    def test_bulk_issuance_import_requires_matching_valid_pdf_and_saves_draft(self):
        Office.objects.create(name="Planning Office", code="planning")
        admin = User.objects.create_user("bulkadmin", password="StrongPass!234", role=Role.ADMIN, is_staff=True)
        self.client.force_login(admin)
        spreadsheet = SimpleUploadedFile(
            "issuances.csv",
            b"reference_number,title,category,year,date_issued,office_code,description,keywords,pdf_filename\nDM-2026-100,Bulk Memo,DIVISION_MEMO,2026,2026-09-16,planning,Imported memo,planning,memo.pdf\n",
            content_type="text/csv",
        )
        pdf = SimpleUploadedFile("memo.pdf", b"%PDF-1.4 bulk", content_type="application/pdf")
        response = self.client.post(
            reverse("core:data_workspace"),
            {"dataset": "issuances", "spreadsheet": spreadsheet, "pdf_files": [pdf]},
        )
        self.assertRedirects(response, reverse("core:data_workspace"))
        item = Issuance.objects.get(reference_number="DM-2026-100")
        self.assertEqual(item.status, "DRAFT")
        self.assertEqual(item.created_by, admin)
