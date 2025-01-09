import os

import config
import requests
from flask import Flask, jsonify, send_from_directory, request
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import check_password_hash
from gevent.pywsgi import WSGIServer
from opds import fromdir
from urllib.parse import quote_plus

app = Flask(__name__, static_url_path="", static_folder="static")
auth = HTTPBasicAuth()

CONTENT_BASE_DIR = '/library'

books_cache = {}


@app.route("/check_and_update_isbns", methods=["POST"])
def check_and_update_isbns():
    """Check all book titles for ISBNs and update the memory if necessary."""
    try:
        books_data = {}

        for title in books_data:
            if not books_data[title]:
                print(f"Fetching ISBN for: {title}")
                isbns = get_isbn_from_google_books(title)
                if isbns:
                    books_data[title] = isbns
                else:
                    books_data[title] = []  # No ISBN found

        print(f"Books data to be saved: {books_data}")
        print("ISBN data updated.")

        return jsonify({"message": "ISBN data successfully updated"}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to update ISBN data"}), 500


@auth.verify_password
def verify_password(username, password):
    if not config.TEENYOPDS_ADMIN_PASSWORD:
        return True
    elif username in config.users and check_password_hash(
            config.users.get(username), password
    ):
        return username


@app.route("/")
@app.route("/healthz")
def healthz():
    return "ok"


@app.route("/content/<path:path>")
@auth.login_required
def send_content(path):
    return send_from_directory(config.CONTENT_BASE_DIR, path)


@app.route("/catalog")
@app.route("/catalog/<path:path>")
@auth.login_required
def catalog(path=""):
    view_mode = request.args.get("view", "list")  # default to 'list' view
    c = fromdir(request.root_url, request.url, config.CONTENT_BASE_DIR, path)

    catalog_entries = []
    for entry in c.entries:
        title = entry.title
        isbn = get_isbn_from_google_books(title)
        entry.isbn = isbn if isbn else []
        catalog_entries.append(entry)

    return c.render(view_mode=view_mode, catalog_entries=catalog_entries)


@app.route("/isbn_lookup", methods=["POST"])
def isbn_lookup():
    """Endpoint to get ISBNs for a list of book titles."""
    try:
        request_data = request.get_json()
        book_titles = request_data.get("book_titles", [])

        if not book_titles:
            return jsonify({"error": "No book titles provided"}), 400

        books_data = {}
        result = {}
        for title in book_titles:
            if title in books_data and books_data[title]:
                result[title] = books_data[title]
            else:
                isbns = get_isbn_from_google_books(title)
                result[title] = isbns
                if isbns:
                    books_data[title] = isbns
                else:
                    books_data[title] = []

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_isbn_from_google_books(title):
    """Fetch ISBN from Google Books API based on book title."""
    title = quote_plus(title)
    url = f"https://www.googleapis.com/books/v1/volumes?q=intitle:{title}&maxResults=1&key={os.getenv('GOOGLE_BOOKS_API_KEY')}"
    print(f"Fetching ISBN for: {title} | URL: {url}")  # Debugging: Log the request URL
    response = requests.get(url)

    if response.status_code != 200:
        print(f"Failed to fetch data for {title}. Status code: {response.status_code}")
        return []

    data = response.json()
    print(f"API response for {title}: {data}")  # Debugging: Print raw response

    # Extract the ISBN (13 digits)
    isbn_list = []
    if "items" in data:
        for item in data["items"]:
            volume_info = item.get("volumeInfo", {})
            industry_identifiers = volume_info.get("industryIdentifiers", [])
            for identifier in industry_identifiers:
                if identifier["type"] == "ISBN_13":
                    isbn_list.append(identifier["identifier"])

    if not isbn_list:
        print(f"No ISBN found for {title}")  # Debugging: Log if no ISBN is found
    return isbn_list


if __name__ == "__main__":
    http_server = WSGIServer(("", 5000), app)
    http_server.serve_forever()
