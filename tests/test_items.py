"""
Unit tests for items CRUD REST endpoints.
"""

from fastapi.testclient import TestClient


def test_get_items(client: TestClient):
    """Verify listing items returns populated initial samples."""
    response = client.get("/api/v1/items")
    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 5


def test_create_item(client: TestClient):
    """Verify creating an item adds it to store."""
    payload = {
        "name": "Custom Kubernetes Ingress",
        "description": "High performance load balanced ingress controller",
        "price": 0.05,
        "tags": ["network", "k8s"],
    }
    response = client.post("/api/v1/items", json=payload)
    assert response.status_code == 201
    item = response.json()
    assert item["name"] == payload["name"]
    assert "id" in item

    # Verify retrieval
    get_res = client.get(f"/api/v1/items/{item['id']}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == payload["name"]


def test_get_nonexistent_item_404(client: TestClient):
    """Verify 404 for missing UUID."""
    response = client.get("/api/v1/items/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_update_item(client: TestClient):
    """Verify full update of an existing item."""
    items = client.get("/api/v1/items").json()
    item_id = items[0]["id"]

    update_payload = {
        "name": "Updated Instance Type",
        "description": "New description",
        "price": 0.35,
        "tags": ["updated"],
    }
    response = client.put(f"/api/v1/items/{item_id}", json=update_payload)
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Instance Type"


def test_delete_item(client: TestClient):
    """Verify deleting an item removes it."""
    items = client.get("/api/v1/items").json()
    item_id = items[0]["id"]

    del_res = client.delete(f"/api/v1/items/{item_id}")
    assert del_res.status_code == 204

    get_res = client.get(f"/api/v1/items/{item_id}")
    assert get_res.status_code == 404
