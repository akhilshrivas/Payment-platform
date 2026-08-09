"""
Shared pytest fixtures for all tests.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


@pytest.fixture
def api_client() -> APIClient:
    """Unauthenticated DRF test client."""
    return APIClient()


@pytest.fixture
def create_user(db):
    """Factory fixture for creating test users."""

    def _create_user(
        email: str = "test@example.com",
        password: str = "TestPass123!",
        first_name: str = "Test",
        last_name: str = "User",
        **kwargs,
    ) -> User:
        return User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            **kwargs,
        )

    return _create_user


@pytest.fixture
def user(create_user) -> User:
    """A single test user instance."""
    return create_user()


@pytest.fixture
def another_user(create_user) -> User:
    """A second test user instance."""
    return create_user(email="another@example.com", first_name="Another", last_name="User")


@pytest.fixture
def auth_client(api_client, user) -> tuple[APIClient, User]:
    """Authenticated API client (returns client, user)."""
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client, user


@pytest.fixture
def another_auth_client(api_client, another_user) -> tuple[APIClient, User]:
    """Authenticated API client for the second user."""
    client = APIClient()
    refresh = RefreshToken.for_user(another_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client, another_user
