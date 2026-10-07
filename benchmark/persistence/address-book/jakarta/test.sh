#!/usr/bin/env bash
set -euo pipefail
python3 - <<'PYTEST'
import os, time
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

app = "address-book"
profile = os.environ.get("SCARF_TARGET", "quarkus")
assert profile in ("spring", "jakarta", "quarkus"), profile
port = 9080 if profile == "jakarta" else (8081 if app == "order" and profile == "spring" else 8082 if app == "order" else 8080)
context = f"/{app}-10-SNAPSHOT" if profile == "jakarta" else ""
base = os.environ.get("BASE_URL", f"http://localhost:{port}{context}").rstrip("/")
assert urlsplit(base).path == context, f"Expected exact context {context!r}, got {urlsplit(base).path!r}"
path = "/orders" if app == "order" and profile == "quarkus" else "/order.xhtml" if app == "order" else "/index.xhtml"
url = base + path

def require(ok, message):
    if not ok: raise AssertionError(message)

def open_exact(page, link):
    response = page.goto(link, wait_until="domcontentloaded", timeout=15000)
    require(response is not None and response.status == 200, f"Expected 200 at exact path {link}; got {response.status if response else None}")
    require(page.url == link, f"Expected exact final URL {link}, got {page.url}")

def field(page, name):
    return page.locator(f'input[id="{name}"], input[id$=":{name}"]').first

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
    page=browser.new_page()
    deadline=time.monotonic()+300
    while True:
        try:
            open_exact(page,url)
            break
        except Exception:
            if time.monotonic()>deadline: raise
            time.sleep(2)
    if app == "address-book":
        require("Welcome to the Address Book example." in page.locator("body").inner_text(), "Missing address book home")
        open_exact(page,base+"/contact/Create.xhtml")
        field(page,"firstName").fill("Scarf")
        field(page,"lastName").fill("Contact")
        field(page,"email").fill("scarf.contact@example.org")
        field(page,"homePhone").fill("2125550100")
        field(page,"mobilePhone").fill("2125550101")
        page.get_by_role("link",name="Save",exact=True).click()
        page.wait_for_load_state("domcontentloaded")
        saved_body=page.locator("body").inner_text()
        require("Contact was successfully created." in saved_body,f"Save did not confirm creation: {saved_body[:1000]!r}")
        open_exact(page,base+"/contact/List.xhtml")
        body=page.locator("body").inner_text()
        require(all(x in body for x in ("Scarf","Contact","scarf.contact@example.org")),f"Saved contact missing: {body[:1000]!r}")
    else:
        require("Order ID" in page.locator("body").inner_text(), "Missing order form")
        order_id=str(670000+int(time.time())%100000)
        field(page,"orderIdInputText").fill(order_id)
        field(page,"shipmentInfoInputText").fill("Scarf shipment")
        page.locator('select[id="statusMenu"], select[id$=":statusMenu"]').select_option("N")
        page.locator('select[id="discountMenu"], select[id$=":discountMenu"]').select_option("5")
        page.get_by_role("button",name="Submit",exact=True).click()
        page.wait_for_load_state("domcontentloaded")
        open_exact(page,url)
        body=page.locator("body").inner_text()
        require(order_id in body and "Scarf shipment" in body,f"Saved order missing: {body[:1000]!r}")
    browser.close()
print(f"PASS {app} ({profile}): exact paths and persisted data")
PYTEST
