import os
import json
import requests
from flask import Flask, jsonify, send_from_directory, request
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import check_password_hash
from gevent.pywsgi import WSGIServer
from opds import fromdir
import config

app = Flask(__name__, static_url_path="", static_folder="static")
auth = HTTPBasicAuth()

BOOKS_ISBN_FILE = os.path.join(app.root_path, 'books_isbn.json')
CONTENT_BASE_DIR = '/library'


@app.route("/check_and_update_isbns", methods=["POST"])
def check_and_update_isbns():
    """Check all book titles for ISBNs and update the JSON file if necessary."""
    try:
        books_data = load_books_isbn()

        # Loop through all books in the data and update missing ISBNs
        for title in books_data:
            if not books_data[title]:  # If no ISBN is associated with the title
                print(f"Fetching ISBN for: {title}")
                isbns = get_isbn_from_google_books(title)
                if isbns:
                    books_data[title] = isbns
                else:
                    books_data[title] = []  # No ISBN found

        # Save updated data back to the JSON file
        print(f"Books data to be saved: {books_data}")
        save_books_isbn(books_data)
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
    # Check for view_mode parameter in the URL query string
    view_mode = request.args.get("view", "list")  # default to 'list' view
    c = fromdir(request.root_url, request.url, config.CONTENT_BASE_DIR, path)
    return c.render(view_mode=view_mode)


@app.route("/isbn_lookup", methods=["POST"])
def isbn_lookup():
    """Endpoint to get ISBNs for a list of book titles."""
    try:
        # Get the JSON payload from the request
        request_data = request.get_json()
        book_titles = request_data.get("book_titles", [])

        if not book_titles:
            return jsonify({"error": "No book titles provided"}), 400

        # Load current book data from the JSON file
        books_data = load_books_isbn()

        result = {}
        for title in book_titles:
            # Check if the book already has an ISBN associated with it
            if title in books_data and books_data[title]:
                result[title] = books_data[title]
            else:
                # If no ISBN, fetch it from Google Books API
                isbns = get_isbn_from_google_books(title)
                result[title] = isbns
                # If ISBN is found, update the JSON file
                if isbns:
                    books_data[title] = isbns
                else:
                    books_data[title] = []

        # Save the updated book data back to the JSON file
        save_books_isbn(books_data)

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_isbn_from_google_books(title):
    """Fetch ISBN from Google Books API based on book title."""
    url = f"https://www.googleapis.com/books/v1/volumes?q=intitle:{title}&maxResults=1"
    response = requests.get(url)
    data = response.json()

    # Extract the ISBN (13 digits)
    isbn_list = []
    if "items" in data:
        for item in data["items"]:
            volume_info = item.get("volumeInfo", {})
            industry_identifiers = volume_info.get("industryIdentifiers", [])
            for identifier in industry_identifiers:
                if identifier["type"] == "ISBN_13":
                    isbn_list.append(identifier["identifier"])

    return isbn_list


def load_books_isbn():
    # Load the existing ISBN data from the JSON file if it exists
    if os.path.exists(BOOKS_ISBN_FILE):
        with open(BOOKS_ISBN_FILE, 'r') as f:
            books_data = json.load(f)
            print(f"Loaded books data: {books_data}")  # Debugging line
    else:
        books_data = {}

    # Get book titles from file names in the library directory
    for filename in os.listdir(CONTENT_BASE_DIR):
        if filename.endswith(('.pdf', '.epub', '.mobi', '.fb2')):  # Adjust extensions as needed
            book_title = filename.split('.')[0]  # Assuming file names are book titles
            if book_title not in books_data:
                books_data[book_title] = []  # Add empty ISBN list if the book title isn't in the JSON

    return books_data


def save_books_isbn(data):
    try:
        print(f"Saving ISBN data to: {BOOKS_ISBN_FILE}", flush=True)
        with open(BOOKS_ISBN_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving ISBN data: {e}")


if __name__ == "__main__":
    # Start the WSGI server after checking and updating ISBNs
    http_server = WSGIServer(("", 5000), app)
    http_server.serve_forever()
