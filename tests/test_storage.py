from __future__ import annotations

from contextlib import closing

from thinkspace.storage import (
  connect,
  delete_note,
  get_note,
  iter_recent,
  search_notes,
)


def test_insert_and_search(scoped_db, insert_sample):
  with closing(connect()) as conn:
    nid = insert_sample(conn, 'fix env var issue')
    rows = search_notes(conn, 'env', project='demo', limit=10)
    assert any(r.id == nid for r in rows)
    assert rows[0].project == 'demo'


def test_delete_note_is_idempotent(scoped_db, insert_sample):
  with closing(connect()) as conn:
    nid = insert_sample(conn, 'remove this note')
    assert get_note(conn, nid) is not None
    assert delete_note(conn, nid) is True
    assert delete_note(conn, nid) is False
    assert get_note(conn, nid) is None
    assert not any(r.id == nid for r in search_notes(conn, 'remove'))


def test_iter_recent_respects_limit_and_order(scoped_db, insert_sample):
  with closing(connect()) as conn:
    ids = [insert_sample(conn, f'note {idx}') for idx in range(5)]
    recent = list(iter_recent(conn, limit=3))
    assert [n.id for n in recent] == ids[::-1][:3]
    assert all(n.text.startswith('note') for n in recent)


def test_search_notes_falls_back_to_like(scoped_db, insert_sample, monkeypatch):
  monkeypatch.setattr('thinkspace.storage.has_fts5', lambda _: False)
  with closing(connect()) as conn:
    insert_sample(conn, 'Alpha beta gamma')
    insert_sample(conn, 'delta epsilon')
    matches = search_notes(conn, 'beta', project=None, limit=5)
    assert len(matches) == 1
    assert matches[0].text == 'Alpha beta gamma'
