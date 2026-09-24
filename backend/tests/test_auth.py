"""Auth tests — login, JWT handling, RBAC gates, hashing, account rules."""

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.dependencies import can_manage_role
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models import User
from app.models.enums import UserRole

PASSWORD = "Test123!"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"
ADMIN_URL = "/api/v1/protected/admin"
STAFF_URL = "/api/v1/protected/staff"


@pytest.fixture
async def users(engine):
    """One active user per role plus one inactive faculty account."""
    factory = async_sessionmaker(engine, expire_on_commit=False)
    specs = [
        ("superadmin", "Super Admin", "super@x.edu", UserRole.SUPER_ADMIN, True),
        ("admin", "Admin", "admin@x.edu", UserRole.ADMIN, True),
        ("faculty", "Faculty", "fac@x.edu", UserRole.FACULTY, True),
        ("student", "Student", "stu@x.edu", UserRole.STUDENT, True),
        ("inactive", "Inactive", "off@x.edu", UserRole.FACULTY, False),
    ]
    created = {}
    async with factory() as session:
        for key, name, email, role, active in specs:
            user = User(
                name=name, email=email, password_hash=hash_password(PASSWORD),
                role=role, is_active=active,
            )
            session.add(user)
            created[key] = user
        await session.commit()
        for user in created.values():
            await session.refresh(user)
    return created


def _login(client, email, password=PASSWORD):
    return client.post(LOGIN_URL, json={"email": email, "password": password})


def _headers_for(client, email, password=PASSWORD):
    token = _login(client, email, password).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("key,role", [
    ("superadmin", UserRole.SUPER_ADMIN),
    ("admin", UserRole.ADMIN),
    ("faculty", UserRole.FACULTY),
    ("student", UserRole.STUDENT),
])
async def test_login_success_each_role(client, users, key, role):
    response = _login(client, users[key].email)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert "password_hash" not in body
    claims = decode_access_token(body["access_token"])
    assert claims["sub"] == str(users[key].id)
    assert claims["role"] == role.value


async def test_login_is_case_insensitive_on_email(client, users):
    assert _login(client, "ADMIN@X.EDU").status_code == 200


async def test_login_unknown_email_rejected(client):
    response = _login(client, "nobody@x.edu")
    assert response.status_code == 401
    assert "detail" in response.json()


async def test_login_wrong_password_rejected(client, users):
    assert _login(client, users["admin"].email, "wrong-password").status_code == 401


async def test_login_inactive_user_rejected(client, users):
    # Inactive accounts get the same 401 as bad credentials (no enumeration).
    assert _login(client, users["inactive"].email).status_code == 401


async def test_me_returns_profile_without_hash(client, users):
    response = client.get(ME_URL, headers=_headers_for(client, users["faculty"].email))
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == users["faculty"].email
    assert body["role"] == UserRole.FACULTY.value
    assert "password_hash" not in body


async def test_me_missing_token_rejected(client):
    response = client.get(ME_URL)
    assert response.status_code == 401


async def test_me_invalid_token_rejected(client):
    response = client.get(ME_URL, headers={"Authorization": "Bearer not-a-token"})
    assert response.status_code == 401


async def test_me_wrong_scheme_rejected(client, users):
    token = _login(client, users["admin"].email).json()["access_token"]
    response = client.get(ME_URL, headers={"Authorization": f"Token {token}"})
    assert response.status_code == 401


async def test_me_expired_token_rejected(client, users):
    token = create_access_token(
        subject=users["admin"].id, role=UserRole.ADMIN.value, expires_minutes=-1
    )
    response = client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Token expired"


async def test_me_inactive_user_forbidden(client, users):
    token = create_access_token(
        subject=users["inactive"].id, role=UserRole.FACULTY.value
    )
    response = client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


async def test_me_deleted_user_rejected(client, users, engine):
    token = _login(client, users["student"].email).json()["access_token"]
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        await session.delete(users["student"])
        await session.commit()
    response = client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


@pytest.mark.parametrize("key,expected_admin,expected_staff", [
    ("superadmin", 200, 200),
    ("admin", 200, 200),
    ("faculty", 403, 200),
    ("student", 403, 403),
])
async def test_role_surfaces(client, users, key, expected_admin, expected_staff):
    headers = _headers_for(client, users[key].email)
    assert client.get(ADMIN_URL, headers=headers).status_code == expected_admin
    assert client.get(STAFF_URL, headers=headers).status_code == expected_staff


@pytest.mark.parametrize("url", [ADMIN_URL, STAFF_URL])
async def test_surfaces_require_authentication(client, url):
    assert client.get(url).status_code == 401


@pytest.mark.parametrize("actor,target,expected", [
    (UserRole.SUPER_ADMIN, UserRole.SUPER_ADMIN, True),
    (UserRole.SUPER_ADMIN, UserRole.ADMIN, True),
    (UserRole.SUPER_ADMIN, UserRole.STUDENT, True),
    (UserRole.ADMIN, UserRole.ADMIN, True),
    (UserRole.ADMIN, UserRole.FACULTY, True),
    (UserRole.ADMIN, UserRole.SUPER_ADMIN, False),  # admins never manage super-admins
    (UserRole.FACULTY, UserRole.ADMIN, False),
    (UserRole.FACULTY, UserRole.FACULTY, False),
    (UserRole.STUDENT, UserRole.STUDENT, False),
])
def test_account_management_rules(actor, target, expected):
    assert can_manage_role(actor, target) is expected


def test_password_hashing_roundtrip():
    hashed = hash_password(PASSWORD)
    assert hashed != PASSWORD
    assert hashed.startswith("$argon2id$")
    assert verify_password(PASSWORD, hashed) is True
    assert verify_password("wrong", hashed) is False
    assert verify_password(PASSWORD, "not-a-hash") is False


def test_password_hashes_use_random_salts():
    assert hash_password(PASSWORD) != hash_password(PASSWORD)


def test_default_token_lifetime_is_one_hour(users):
    user = users["admin"]
    claims = decode_access_token(
        create_access_token(subject=user.id, role=user.role.value)
    )
    assert claims["exp"] - claims["iat"] == 3600
