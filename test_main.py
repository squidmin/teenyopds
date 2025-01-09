import config
import pytest
from unittest.mock import patch, MagicMock
from flask import Flask, jsonify
from main import app, get_isbn_from_google_books, books_cache


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


def test_healthz(client):
    """Test the /healthz route."""
    response = client.get('/healthz')
    assert response.status_code == 200
    assert response.data == b"ok"


@pytest.mark.parametrize(
    "book_titles, expected_status, expected_json",
    [
        (["The Great Gatsby"], 200, {"The Great Gatsby": ["9780743273565"]}),
        ([], 400, {"error": "No book titles provided"}),
    ]
)
def test_isbn_lookup(client, book_titles, expected_status, expected_json):
    """Test the /isbn_lookup endpoint."""
    with patch('main.get_isbn_from_google_books', return_value=["9780743273565"]):
        response = client.post('/isbn_lookup', json={"book_titles": book_titles})
        assert response.status_code == expected_status
        assert response.get_json() == expected_json


@patch('main.requests.get')
def test_get_isbn_from_google_books(mock_get):
    """Test the function get_isbn_from_google_books."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {
                "volumeInfo": {
                    "industryIdentifiers": [
                        {"type": "ISBN_13", "identifier": "9780743273565"}
                    ]
                }
            }
        ]
    }
    mock_get.return_value = mock_response

    title = "The Great Gatsby"
    isbn = get_isbn_from_google_books(title)
    assert isbn == ["9780743273565"]

    # Modify expected URL to match encoded form (spaces encoded as '+')
    expected_url = f"https://www.googleapis.com/books/v1/volumes?q=intitle:{title.replace(' ', '+')}&maxResults=1&key={None}"
    mock_get.assert_called_once_with(expected_url)


@patch('main.get_isbn_from_google_books')
def test_check_and_update_isbns(mock_get, client):
    """Test the /check_and_update_isbns endpoint."""
    mock_get.return_value = ["9780743273565"]

    response = client.post('/check_and_update_isbns')
    assert response.status_code == 200
    assert response.json == {"message": "ISBN data successfully updated"}

    assert books_cache.get("The Great Gatsby") == ["9780743273565"]


@patch('main.send_from_directory')
def test_send_content(mock_send_from_directory, client):
    """Test the /content/<path> route."""
    mock_send_from_directory.return_value = "Content fetched"
    response = client.get('/content/test_book.pdf')
    mock_send_from_directory.assert_called_once_with(config.CONTENT_BASE_DIR, 'test_book.pdf')
    assert response.data == b"Content fetched"
    assert response.status_code == 200
