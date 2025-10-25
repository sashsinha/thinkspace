from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Callable

import pytest
from typer.testing import CliRunner

from thinkspace.storage import insert_note


@pytest.fixture()
def cli_runner() -> CliRunner:
  return CliRunner()


@pytest.fixture()
def scoped_db(tmp_path, monkeypatch) -> Path:
  """Point the app at an isolated data directory for each test."""
  data_root = tmp_path / 'data-home'
  monkeypatch.setattr(
    'thinkspace.storage.user_data_dir', lambda *_, **__: str(data_root)
  )
  return data_root


@pytest.fixture()
def insert_sample(scoped_db) -> Callable[[sqlite3.Connection, str, str], int]:
  """Insert a sample note using the production code paths."""

  def _insert(conn, text: str, project: str = 'demo') -> int:
    return insert_note(conn, text, project, [f'project:{project}'], Path('.'))

  return _insert
