"""Tests for SaaS auth endpoints: register, login, /me"""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


@pytest.mark.anyio
async def test_register_success(client: AsyncClient) -> None:
    payload = {
        "email": "owner@example.com",
        "password": "securepass123",
        "full_name": "Test Owner",
        "org_name": "Test Org",
        "org_slug": "test-org",
    }
    resp = await client.post("/api/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert data["email"] == "owner@example.com"
    assert data["org_name"] == "Test Org"
    assert data["org_id"] is not None


@pytest.mark.anyio
async def test_register_duplicate_email(client: AsyncClient) -> None:
    payload = {
        "email": "dup@example.com",
        "password": "securepass123",
        "full_name": "Dup User",
        "org_name": "Dup Org",
        "org_slug": "dup-org",
    }
    await client.post("/api/auth/register", json=payload)
    resp = await client.post("/api/auth/register", json=payload)
    assert resp.status_code == 409


@pytest.mark.anyio
async def test_register_duplicate_slug(client: AsyncClient) -> None:
    payload1 = {
        "email": "user1@example.com",
        "password": "pass12345",
        "full_name": "User 1",
        "org_name": "Org 1",
        "org_slug": "same-slug",
    }
    payload2 = {
        "email": "user2@example.com",
        "password": "pass12345",
        "full_name": "User 2",
        "org_name": "Org 2",
        "org_slug": "same-slug",
    }
    await client.post("/api/auth/register", json=payload1)
    resp = await client.post("/api/auth/register", json=payload2)
    assert resp.status_code == 409


@pytest.mark.anyio
async def test_register_weak_password(client: AsyncClient) -> None:
    payload = {
        "email": "weak@example.com",
        "password": "short",
        "full_name": "Weak User",
        "org_name": "Weak Org",
        "org_slug": "weak-org",
    }
    resp = await client.post("/api/auth/register", json=payload)
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_login_success(client: AsyncClient) -> None:
    reg_payload = {
        "email": "login@example.com",
        "password": "mypassword123",
        "full_name": "Login User",
        "org_name": "Login Org",
        "org_slug": "login-org",
    }
    await client.post("/api/auth/register", json=reg_payload)

    resp = await client.post("/api/auth/login", json={"email": "login@example.com", "password": "mypassword123"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["access_token"]
    assert data["email"] == "login@example.com"


@pytest.mark.anyio
async def test_login_wrong_password(client: AsyncClient) -> None:
    reg_payload = {
        "email": "wrongpass@example.com",
        "password": "correctpass123",
        "full_name": "Wrong Pass",
        "org_name": "Wrong Org",
        "org_slug": "wrong-pass-org",
    }
    await client.post("/api/auth/register", json=reg_payload)

    resp = await client.post("/api/auth/login", json={"email": "wrongpass@example.com", "password": "wrongpass"})
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_login_nonexistent_user(client: AsyncClient) -> None:
    resp = await client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "anything"})
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_get_me(client: AsyncClient) -> None:
    reg_payload = {
        "email": "me@example.com",
        "password": "mepass12345",
        "full_name": "Me User",
        "org_name": "Me Org",
        "org_slug": "me-org",
    }
    reg_resp = await client.post("/api/auth/register", json=reg_payload)
    token = reg_resp.json()["access_token"]

    resp = await client.get(f"/api/auth/me?token={token}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["email"] == "me@example.com"
    assert data["full_name"] == "Me User"
