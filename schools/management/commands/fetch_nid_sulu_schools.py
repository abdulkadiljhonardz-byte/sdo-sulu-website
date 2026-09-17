"""Fetch the public Sulu school ID/name directory from DepEd NID."""

import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class NIDSchoolTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.in_row = False
        self.column = 0
        self.school_id_parts = []
        self.school_name = ""

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "tr" and "school-row" in attributes.get("class", ""):
            self.in_row = True
            self.column = 0
            self.school_id_parts = []
            self.school_name = ""
        elif self.in_row and tag == "td":
            self.column += 1
        elif self.in_row and tag == "div" and self.column == 2:
            self.school_name = attributes.get("title", "").strip()

    def handle_data(self, data):
        if self.in_row and self.column == 1:
            self.school_id_parts.append(data)

    def handle_endtag(self, tag):
        if tag != "tr" or not self.in_row:
            return
        school_id = "".join(self.school_id_parts).strip()
        if school_id and self.school_name:
            self.rows.append({"school_id": school_id, "name": self.school_name})
        self.in_row = False


class Command(BaseCommand):
    help = "Fetch all publicly listed Sulu schools from the official DepEd NID dashboard."

    source = "https://nid.deped.gov.ph/public-dashboard/region/BARMM/division/Sulu?page={}"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="deployment/seed_sulu_schools.json",
            help="Project-relative JSON destination.",
        )

    def handle(self, *args, **options):
        output = (Path(settings.BASE_DIR) / options["output"]).resolve()
        deployment_dir = (Path(settings.BASE_DIR) / "deployment").resolve()
        if not output.is_relative_to(deployment_dir):
            raise CommandError("The output path must be inside deployment/.")

        records = {}
        for page in range(1, 11):
            request = Request(self.source.format(page), headers={"User-Agent": "SDO-Sulu-Portal/1.0"})
            with urlopen(request, timeout=30) as response:
                html = response.read().decode("utf-8", errors="replace")
            parser = NIDSchoolTableParser()
            parser.feed(html)
            if not parser.rows:
                raise CommandError(f"No schools found on official NID page {page}.")
            for school in parser.rows:
                records[school["school_id"]] = school
            self.stdout.write(f"Read page {page}: {len(parser.rows)} schools")

        schools = sorted(records.values(), key=lambda item: (item["name"].casefold(), item["school_id"]))
        if len(schools) != 457:
            raise CommandError(f"Expected 457 Sulu schools, received {len(schools)}. Seed was not written.")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(schools, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Saved {len(schools)} official Sulu schools to {output.relative_to(settings.BASE_DIR)}."))
