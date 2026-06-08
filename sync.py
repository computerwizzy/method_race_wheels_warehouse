import csv
import ftplib
import os
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

TIREWEB_USER = os.getenv("TIREWEB_USER")
TIREWEB_PASS = os.getenv("TIREWEB_PASS")
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_PATH = os.getenv("FTP_PATH", "/inventory.csv")

LOGIN_PAGE_URL = "https://method.tireweb.com/Logon/Login"
SEARCH_URL = "https://method.tireweb.com/WheelSearch/ByWheelElements"
SEARCH_PARAMS = {
    "UserTabLinkId": "",
    "RimDiameter": "",
    "RimWidth": "",
    "BoltPattern": "",
    "Bore": "",
    "Brand": "Method Race Wheels",
    "Style": "",
    "Finish": "",
    "Offset": "",
    "WheelSearchType": "0",
}
LOCAL_CSV = "MRW_Inventory_Report.csv"


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def login(session: requests.Session) -> None:
    page = session.get(LOGIN_PAGE_URL)
    page.raise_for_status()
    soup = BeautifulSoup(page.text, "html.parser")
    token_input = soup.find("input", {"name": "__RequestVerificationToken"})
    if not token_input:
        raise RuntimeError("Could not find CSRF token on login page — page structure may have changed")
    token = token_input["value"]
    payload = {
        "Username": TIREWEB_USER,
        "Password": TIREWEB_PASS,
        "RememberMe": "false",
        "__RequestVerificationToken": token,
    }
    resp = session.post(LOGIN_PAGE_URL, data=payload)
    resp.raise_for_status()
    if "Login" in resp.url or "login" in resp.url.lower():
        raise RuntimeError("Login failed — check TIREWEB_USER and TIREWEB_PASS in .env")


def fetch_wheels(session: requests.Session) -> list[dict]:
    response = session.get(SEARCH_URL, params=SEARCH_PARAMS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table")
    if not table:
        raise ValueError("No table found in WheelSearch response")
    # Build index→name map from header row; skip blank headers and mobile-only columns
    header_cells = table.find("tr").find_all(["th", "td"])
    n_cols = len(header_cells)
    named_cols = [
        (i, cell.get_text(strip=True))
        for i, cell in enumerate(header_cells)
        if cell.get_text(strip=True) and i < n_cols
        # skip Image (1) and cols 17-22: empty/button/concatenated-duplicate columns
        and i not in (1, 17, 18, 19, 20, 21, 22)
    ]
    rows = []
    for tr in table.find_all("tr", class_="BuyingTableRow"):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        row = {name: (cells[i] if i < len(cells) else "").rstrip("+")
               for i, name in named_cols}
        rows.append(row)
    if not rows:
        raise ValueError("WheelSearch returned 0 rows — aborting to avoid overwriting FTP with empty file")
    return rows


def write_csv(rows: list[dict], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def upload_ftp(local_path: str) -> None:
    with ftplib.FTP(FTP_HOST) as ftp:
        ftp.login(FTP_USER, FTP_PASS)
        with open(local_path, "rb") as f:
            ftp.storbinary(f"STOR {FTP_PATH}", f)


def main() -> None:
    log("Starting Method Race Wheels inventory sync")
    try:
        session = requests.Session()
        session.headers["User-Agent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )

        log("Logging in to TireWeb...")
        login(session)
        log("Login successful")

        log("Fetching wheel inventory...")
        rows = fetch_wheels(session)
        log(f"Fetched {len(rows)} wheels")

        log("Writing local CSV...")
        write_csv(rows, LOCAL_CSV)

        log(f"Uploading to {FTP_HOST}{FTP_PATH}...")
        upload_ftp(LOCAL_CSV)
        log("Upload complete")

        if os.path.exists(LOCAL_CSV):
            os.remove(LOCAL_CSV)
        log("Sync complete — local CSV deleted")
    except Exception as exc:
        log(f"ERROR: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
