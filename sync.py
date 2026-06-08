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

LOGIN_PAGE_URL = "https://method.tireweb.com/Account/LogOn"
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
LOCAL_CSV = "inventory.csv"


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def login(session: requests.Session) -> None:
    page = session.get(LOGIN_PAGE_URL)
    page.raise_for_status()
    soup = BeautifulSoup(page.text, "html.parser")
    token_input = soup.find("input", {"name": "__RequestVerificationToken"})
    token = token_input["value"] if token_input else ""
    payload = {
        "UserName": TIREWEB_USER,
        "Password": TIREWEB_PASS,
        "RememberMe": "false",
        "__RequestVerificationToken": token,
    }
    resp = session.post(LOGIN_PAGE_URL, data=payload)
    resp.raise_for_status()
    if "LogOn" in resp.url or "login" in resp.url.lower():
        raise RuntimeError("Login failed — check TIREWEB_USER and TIREWEB_PASS in .env")


def fetch_wheels(session: requests.Session) -> list[dict]:
    raise NotImplementedError


def write_csv(rows: list[dict], path: str) -> None:
    raise NotImplementedError


def upload_ftp(local_path: str) -> None:
    raise NotImplementedError


def main() -> None:
    raise NotImplementedError


if __name__ == "__main__":
    main()
