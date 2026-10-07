#!/usr/bin/env bash
set -euo pipefail
python3 - <<'PYTEST'
import os
import time
from playwright.sync_api import sync_playwright
from urllib.parse import urlsplit

app = "simplegreeting"
profile = os.environ.get("SCARF_TARGET", "quarkus")
assert profile in ("spring", "jakarta", "quarkus"), profile
port = 9080 if profile == "jakarta" else 8080
base = os.environ.get("BASE_URL", f"http://localhost:{port}/{app}").rstrip("/")
check_path = urlsplit(base).path
assert check_path == f"/{app}", f"Expected exact application context /{app}, got {check_path}"
url = base + ("/" if profile == "spring" else "/index.xhtml")

def check(condition, message):
    if not condition:
        raise AssertionError(message)

def contains(page, expected):
    body = page.locator("body").inner_text()
    check(expected in body, f"Expected {expected!r} in {page.url}; got {body[:1000]!r}")

def field(page, name):
    return page.locator(f'input[id="{name}"], input[id$=":{name}"]').first

def click(page, label):
    page.get_by_role("button", name=label, exact=True).first.click()
    page.wait_for_load_state("domcontentloaded")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    page = browser.new_page()
    deadline = time.monotonic() + 300
    while True:
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=10000)
            if response and response.status == 200:
                break
        except Exception:
            pass
        if time.monotonic() >= deadline:
            raise AssertionError(f"Expected app at exact path {url}")
        time.sleep(2)
    check(page.url == url, f"Expected exact final URL {url}, got {page.url}")
    if profile != "spring":
        check(page.locator('input[name="jakarta.faces.ViewState"]').count() > 0,
              "Expected JSF form at exact index.xhtml path")

    if app == "billpayment":
        for option, label, amount in (("1", "Debit", "123.45"), ("2", "Credit", "67.89")):
            page.goto(url)
            field(page, "amt" if profile != "spring" else "value").fill(amount)
            page.locator(f'input[type="radio"][value="{option}"]').check()
            click(page, "Pay")
            contains(page, label + " Card:")
            contains(page, amount)
    elif app in ("encoder", "decorators", "producermethods"):
        for coder_type, expected in ([("2", "cc2"), ("1", "input string is aa2, shift value is 2")] if app == "producermethods" else [("2", "cc2")]):
            page.goto(url)
            field(page, "inputString").fill("aa2")
            field(page, "transVal").fill("2")
            if app == "producermethods":
                page.locator(f'input[type="radio"][value="{coder_type}"]').check()
            click(page, "Encode")
            if app == "decorators":
                contains(page, '"aa2" becomes "cc2", 3 characters in length')
            else:
                contains(page, expected)
    elif app == "guessnumber":
        contains(page, "10 guesses")
        field(page, "inputGuess").fill("50")
        click(page, "Guess")
        check("9 guesses" in page.locator("body").inner_text() or "Correct!" in page.locator("body").inner_text(), "Guess gave no feedback")
    elif app == "producerfields":
        for task in ("ScarfTaskAlpha", "ScarfTaskBeta"):
            field(page, "inputString").fill(task)
            click(page, "Submit")
        click(page, "Show Items")
        contains(page, "ScarfTaskAlpha")
        contains(page, "ScarfTaskBeta")
    elif app == "simplegreeting":
        field(page, "name").fill("Scarf")
        click(page, "Say Hello")
        contains(page, "Hi, Scarf!")
    browser.close()
print(f"PASS {app} ({profile}): exact path and behavior")
PYTEST
