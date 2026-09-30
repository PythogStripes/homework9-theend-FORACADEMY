import pytest

pytestmark = pytest.mark.asyncio


async def register_and_login(client, username="anna", password="secret123"):
    await client.post("/register", json={
        "username": username, "email": f"{username}@mail.ru", "password": password})
    resp = await client.post("/login", data={"username": username, "password": password})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# регистрация
async def test_register(client):
    resp = await client.post("/register", json={
        "username": "anna", "email": "anna@mail.ru", "password": "secret123"})
    assert resp.status_code == 201
    assert "password" not in resp.json()


async def test_register_duplicate(client):
    payload = {"username": "anna", "email": "anna@mail.ru", "password": "secret123"}
    await client.post("/register", json=payload)
    assert (await client.post("/register", json=payload)).status_code == 409


# логин
async def test_login_ok(client):
    await register_and_login(client)
    resp = await client.post("/login", data={"username": "anna", "password": "secret123"})
    assert resp.status_code == 200 and resp.json()["access_token"]


async def test_login_wrong_password(client):
    await client.post("/register", json={
        "username": "anna", "email": "anna@mail.ru", "password": "secret123"})
    assert (await client.post("/login", data={"username": "anna", "password": "wrong"})).status_code == 401


# создание проекта
async def test_create_project(client):
    headers = await register_and_login(client)
    resp = await client.post("/projects", json={
        "name": "Course project", "description": "Итоговый проект"}, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["owner_id"] == 1


# обновление проекта владельцем
async def test_update_project_by_owner(client):
    headers = await register_and_login(client)
    project_id = (await client.post("/projects", json={"name": "Old"}, headers=headers)).json()["id"]

    resp = await client.put(f"/projects/{project_id}",
                            json={"name": "New name"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "New name"


# доступ не владельца
async def test_update_project_not_owner(client):
    owner = await register_and_login(client, username="owner")
    project_id = (await client.post("/projects", json={"name": "Not mine"}, headers=owner)).json()["id"]

    intruder = await register_and_login(client, username="intruder")
    resp = await client.put(f"/projects/{project_id}", json={"name": "Hacked!"}, headers=intruder)
    assert resp.status_code == 403
    assert (await client.delete(f"/projects/{project_id}", headers=intruder)).status_code == 403


# ошибки 404 и 401
async def test_project_not_found(client):
    headers = await register_and_login(client)
    assert (await client.get("/projects/999", headers=headers)).status_code == 404


async def test_projects_require_auth(client):
    assert (await client.get("/projects")).status_code == 401