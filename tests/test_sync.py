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
