"""Tests for GET /health endpoint."""

import pytest


def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_health_body_structure(client):
    response = client.get("/health")
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "service" in data


def test_health_service_name(client):
    response = client.get("/health")
    data = response.json()
    assert "QuensultingAI" in data["service"] or "Dental" in data["service"]


def test_health_content_type(client):
    response = client.get("/health")
    assert "application/json" in response.headers["content-type"]
