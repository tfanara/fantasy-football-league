import json
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from urllib.parse import urlencode


# ---------------------------------------------------------
# LOAD CREDENTIALS
# ---------------------------------------------------------

with open("yahoo_credentials.json", "r") as f:
    credentials = json.load(f)

client_id = credentials["client_id"]


# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------

HOST = "localhost"
PORT = 8000

redirect_uri = f"https://{HOST}:{PORT}"
authorize_url = "https://api.login.yahoo.com/oauth2/request_auth"


# ---------------------------------------------------------
# CALLBACK HANDLER
# ---------------------------------------------------------

authorization_code = None


class CallbackHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        global authorization_code

        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if "code" in params:
            authorization_code = params["code"][0]

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()

            self.wfile.write(
                b"""
                <html>
                <body>
                <h1>Yahoo authorization received!</h1>
                <p>You can close this browser window.</p>
                </body>
                </html>
                """
            )

        else:
            self.send_response(400)
            self.end_headers()

            self.wfile.write(
                b"No authorization code received."
            )

    def log_message(self, format, *args):
        pass


# ---------------------------------------------------------
# START SERVER
# ---------------------------------------------------------

server = HTTPServer(
    (HOST, PORT),
    CallbackHandler
)

thread = threading.Thread(
    target=server.serve_forever,
    daemon=True
)

thread.start()


# ---------------------------------------------------------
# BUILD AUTHORIZATION URL
# ---------------------------------------------------------

params = {
    "client_id": client_id,
    "redirect_uri": redirect_uri,
    "response_type": "code",
}

url = authorize_url + "?" + urlencode(params)


print()
print("Yahoo OAuth authorization")
print("=" * 60)
print()
print("Opening browser...")
print()
print("Authorization URL:")
print(url)
print()


# ---------------------------------------------------------
# OPEN BROWSER
# ---------------------------------------------------------

webbrowser.open(url)


# ---------------------------------------------------------
# WAIT FOR CALLBACK
# ---------------------------------------------------------

print("Waiting for Yahoo authorization...")
print()

while authorization_code is None:
    pass


server.shutdown()


print()
print("Authorization code received!")
print("=" * 60)
print("OAuth flow completed successfully.")
print()