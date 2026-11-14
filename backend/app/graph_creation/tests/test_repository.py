"""Supabase failures must say what to fix, not return a blank 500."""

from __future__ import annotations

from postgrest.exceptions import APIError

from app.graph_creation.repository import SupabaseRequestError, _describe_api_error


def _api_error(**payload: object) -> APIError:
    base = {"message": "", "code": None, "hint": None, "details": None}
    return APIError({**base, **payload})


def test_rls_violation_points_at_the_service_role_key() -> None:
    error = _api_error(
        message='new row violates row-level security policy for table "projects"',
        code="42501",
    )

    text = _describe_api_error(error)

    assert "Supabase rejected the request" in text
    assert "row-level security" in text
    assert "SUPABASE_SERVICE_ROLE_KEY" in text


def test_other_errors_keep_the_message_and_hint() -> None:
    error = _api_error(
        message='relation "files" does not exist',
        code="42P01",
        hint="run the migration",
    )

    text = _describe_api_error(error)

    assert "relation" in text
    assert "hint: run the migration" in text
    assert "SUPABASE_SERVICE_ROLE_KEY" not in text


def test_error_is_an_http_500_with_the_message() -> None:
    error = SupabaseRequestError("boom")

    assert error.status_code == 500
    assert error.detail == "boom"


def test_missing_owner_foreign_key_points_at_dev_user_id() -> None:
    error = _api_error(
        message='insert or update on table "projects" violates foreign key constraint',
        code="23503",
    )

    text = _describe_api_error(error)

    assert "DEV_USER_ID" in text
    assert "Authentication -> Users" in text


def test_duplicate_path_is_explained() -> None:
    error = _api_error(
        message='duplicate key value violates unique constraint "files_project_id_path_key"',
        code="23505",
    )

    assert "already exists" in _describe_api_error(error)
