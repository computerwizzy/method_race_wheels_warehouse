import csv
import ftplib
import os
from unittest.mock import MagicMock, patch

import pytest

# Set env vars before importing sync so dotenv doesn't overwrite them
os.environ["TIREWEB_USER"] = "test_user"
os.environ["TIREWEB_PASS"] = "test_pass"
os.environ["FTP_HOST"] = "ftp.test.com"
os.environ["FTP_USER"] = "ftp_user"
os.environ["FTP_PASS"] = "ftp_pass"
os.environ["FTP_PATH"] = "/inventory.csv"

import sync  # noqa: E402

MOCK_LOGIN_PAGE = """
<html><body>
<form>
  <input name="__RequestVerificationToken" value="tok_abc123" />
</form>
</body></html>
"""

MOCK_WHEELS_HTML = """
<html><body>
<table>
  <thead>
    <tr><th>Part Number</th><th>Description</th><th>Price</th><th>Stock</th></tr>
  </thead>
  <tbody>
    <tr><td>301-5883B</td><td>Method 301 18x9 Black</td><td>$299.99</td><td>5</td></tr>
    <tr><td>305-7883C</td><td>Method 305 20x10 Chrome</td><td>$399.99</td><td>2</td></tr>
  </tbody>
</table>
</body></html>
"""


class TestLogin:
    def _make_session(self, post_redirect_url: str) -> MagicMock:
        session = MagicMock()
        login_page = MagicMock()
        login_page.text = MOCK_LOGIN_PAGE
        post_resp = MagicMock()
        post_resp.url = post_redirect_url
        session.get.return_value = login_page
        session.post.return_value = post_resp
        return session

    def test_sends_credentials_and_csrf_token(self):
        session = self._make_session("https://method.tireweb.com/Home")
        sync.login(session)
        _, call_kwargs = session.post.call_args
        data = call_kwargs["data"]
        assert data["UserName"] == "test_user"
        assert data["Password"] == "test_pass"
        assert data["__RequestVerificationToken"] == "tok_abc123"

    def test_raises_when_redirected_back_to_logon(self):
        session = self._make_session("https://method.tireweb.com/Account/LogOn")
        with pytest.raises(RuntimeError, match="Login failed"):
            sync.login(session)

    def test_raises_when_csrf_token_not_found(self):
        session = MagicMock()
        login_page = MagicMock()
        login_page.text = "<html><body><form></form></body></html>"
        session.get.return_value = login_page
        with pytest.raises(RuntimeError, match="CSRF token"):
            sync.login(session)


class TestFetchWheels:
    def test_parses_table_into_list_of_dicts(self):
        session = MagicMock()
        resp = MagicMock()
        resp.text = MOCK_WHEELS_HTML
        session.get.return_value = resp

        rows = sync.fetch_wheels(session)

        assert len(rows) == 2
        assert rows[0]["Part Number"] == "301-5883B"
        assert rows[0]["Price"] == "$299.99"
        assert rows[1]["Description"] == "Method 305 20x10 Chrome"
        assert rows[1]["Stock"] == "2"

    def test_raises_when_no_table_in_response(self):
        session = MagicMock()
        resp = MagicMock()
        resp.text = "<html><body><p>No results</p></body></html>"
        session.get.return_value = resp

        with pytest.raises(ValueError, match="No table found"):
            sync.fetch_wheels(session)

    def test_raises_when_table_has_zero_data_rows(self):
        session = MagicMock()
        resp = MagicMock()
        resp.text = """
        <html><body>
        <table>
          <thead><tr><th>Part Number</th></tr></thead>
          <tbody></tbody>
        </table>
        </body></html>
        """
        session.get.return_value = resp

        with pytest.raises(ValueError, match="0 rows"):
            sync.fetch_wheels(session)

    def test_requests_correct_url_and_params(self):
        session = MagicMock()
        resp = MagicMock()
        resp.text = MOCK_WHEELS_HTML
        session.get.return_value = resp

        sync.fetch_wheels(session)

        call_args, call_kwargs = session.get.call_args
        assert call_args[0] == sync.SEARCH_URL
        assert call_kwargs["params"]["Brand"] == "Method Race Wheels"


class TestWriteCsv:
    def test_writes_header_and_all_rows(self, tmp_path):
        rows = [
            {"Part Number": "301-5883B", "Price": "$299.99", "Stock": "5"},
            {"Part Number": "305-7883C", "Price": "$399.99", "Stock": "2"},
        ]
        path = str(tmp_path / "out.csv")

        sync.write_csv(rows, path)

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            result = list(reader)

        assert len(result) == 2
        assert result[0]["Part Number"] == "301-5883B"
        assert result[1]["Stock"] == "2"

    def test_csv_header_matches_dict_keys(self, tmp_path):
        rows = [{"A": "1", "B": "2"}]
        path = str(tmp_path / "out.csv")

        sync.write_csv(rows, path)

        with open(path, newline="", encoding="utf-8") as f:
            header_line = f.readline().strip()

        assert header_line == "A,B"
