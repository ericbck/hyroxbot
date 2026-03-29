"""
HYROX Auto-Booking Script
Books HYROX Performance (18:30-19:45, Monday) via the Yolawo guest form.
Runs headlessly in CI; pass --show to watch locally.
"""

import sys
from datetime import date, timedelta
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
FIRST_NAME = "Eric"
LAST_NAME  = "Baack"
EMAIL      = "eric.baack@outlook.com"
PHONE      = "017684808571"

WIDGET_ID = "687a0408baa821731836a2c3"

# The bookable ID increments by 1 (hex) each week.
# Anchor: ISO week 13 of 2026 → "691b070a81863aa9fbd22e83"
_BASE_BOOKABLE_ID = "691b070a81863aa9fbd22e83"
_BASE_YEAR, _BASE_WEEK = 2026, 13


def get_next_monday() -> date:
    today = date.today()
    days = (7 - today.weekday()) % 7 or 7
    return today + timedelta(days=days)


def bookable_id_for(target: date) -> str:
    base_monday = date.fromisocalendar(_BASE_YEAR, _BASE_WEEK, 1)
    week_offset = (target - base_monday).days // 7
    new_id_int = int(_BASE_BOOKABLE_ID, 16) + week_offset
    return format(new_id_int, "024x")


SKIP_FILE = "skip.txt"


def book(headless: bool = True) -> None:
    # Check skip flag
    with open(SKIP_FILE, "r") as f:
        if f.read().strip().upper() == "SKIP":
            print("SKIP detected — not booking this week.")
            with open(SKIP_FILE, "w") as fw:
                fw.write("")
            return

    monday = get_next_monday()
    bookable = bookable_id_for(monday)
    join_url = f"https://widgets.yolawo.de/w/{WIDGET_ID}/bookables/{bookable}/join"
    iso = monday.isocalendar()
    print(f"Booking HYROX Performance 18:30 — {monday} (W{iso[1]}/{iso[0]})")
    print(f"Bookable ID: {bookable}")
    print(f"Form URL: {join_url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_context(viewport={"width": 1280, "height": 900}).new_page()

        # 1. Open the registration form
        page.goto(join_url, wait_until="networkidle")
        page.wait_for_selector("input", timeout=30000)
        print("Form loaded.")

        # 2. Fill in personal details
        page.locator("#mat-input-0").fill(FIRST_NAME)
        page.wait_for_timeout(500)
        page.locator("#mat-input-1").fill(LAST_NAME)
        page.wait_for_timeout(500)
        page.locator("#mat-input-2").fill(EMAIL)
        page.wait_for_timeout(500)
        page.locator("#mat-input-3").fill(PHONE)
        page.wait_for_timeout(500)
        print("Fields filled.")

        # 3. Check all checkboxes (click the visible label, not the hidden input)
        for cb in page.locator("mat-checkbox").all():
            if not cb.locator("input").is_checked():
                cb.click()
                page.wait_for_timeout(300)
        print("Checkboxes checked.")

        # 4. Submit
        page.get_by_role("button", name="Jetzt anmelden").click()
        print("Clicked 'Jetzt anmelden'.")

        # 5. Verify confirmation
        try:
            page.wait_for_selector(
                ":is("
                ":has-text('erfolgreich'),"
                ":has-text('Bestätigung'),"
                ":has-text('confirmed'),"
                ":has-text('Danke')"
                ")",
                timeout=15000,
            )
            print("SUCCESS: Booking confirmed!")
        except PlaywrightTimeout:
            print("WARNING: Could not detect confirmation text. Saving screenshot.")
            page.screenshot(path="booking_result.png")
            sys.exit(1)
        finally:
            browser.close()


if __name__ == "__main__":
    headless = "--show" not in sys.argv
    book(headless=headless)
