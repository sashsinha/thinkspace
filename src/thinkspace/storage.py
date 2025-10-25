from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple, cast

from platformdirs import user_data_dir

APP_NAME = 'thinkspace'
APP_AUTHOR = 'Thinkspace'


def db_path() -> Path:
  data_dir = Path(user_data_dir(APP_NAME, APP_AUTHOR))
  data_dir.mkdir(parents=True, exist_ok=True)
  return data_dir / 'notes.db'


def connect() -> sqlite3.Connection:
  path = db_path()
  conn = sqlite3.connect(path)
  conn.row_factory = sqlite3.Row
  _ensure_schema(conn)
  return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
  cur = conn.cursor()
  cur.execute(
    """
        CREATE TABLE IF NOT EXISTS notes(
            id INTEGER PRIMARY KEY,
            text TEXT NOT NULL,
            project TEXT NOT NULL,
            tags TEXT NOT NULL,
            created_at TEXT NOT NULL,
            path TEXT NOT NULL
        );
        """
  )
  # Try to create FTS5 table; ignore if extension not available
  try:
    cur.execute(
      """
            CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts
            USING fts5(text, project, tags, content='notes', content_rowid='id');
            """
    )
    # Ensure content sync triggers
    cur.executescript(
      """
            CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
                INSERT INTO notes_fts(rowid, text, project, tags) VALUES (new.id, new.text, new.project, new.tags);
            END;
            CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
                INSERT INTO notes_fts(notes_fts, rowid, text, project, tags) VALUES('delete', old.id, old.text, old.project, old.tags);
            END;
            CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
                INSERT INTO notes_fts(notes_fts, rowid, text, project, tags) VALUES('delete', old.id, old.text, old.project, old.tags);
                INSERT INTO notes_fts(rowid, text, project, tags) VALUES (new.id, new.text, new.project, new.tags);
            END;
            """
    )
  except sqlite3.OperationalError:
    # FTS5 not available; searches will fallback
    pass
  conn.commit()


def has_fts5(conn: sqlite3.Connection) -> bool:
  try:
    conn.execute('CREATE VIRTUAL TABLE IF NOT EXISTS __ftscheck USING fts5(x);')
    conn.execute('DROP TABLE IF EXISTS __ftscheck;')
    return True
  except sqlite3.OperationalError:
    return False


def now_iso() -> str:
  return datetime.now(timezone.utc).isoformat()


@dataclass
class Note:
  id: int
  text: str
  project: str
  tags: str
  created_at: str
  path: str


def insert_note(
  conn: sqlite3.Connection,
  text: str,
  project: str,
  tags: Sequence[str],
  path: Path,
) -> int:
  cur = conn.cursor()
  created_at = now_iso()
  tags_str = ','.join(sorted(set(tags)))
  cur.execute(
    'INSERT INTO notes(text, project, tags, created_at, path) VALUES (?, ?, ?, ?, ?)',
    (text, project, tags_str, created_at, str(path)),
  )
  conn.commit()
  return cast(int, cur.lastrowid)


def iter_recent(conn: sqlite3.Connection, limit: int = 20) -> Iterable[Note]:
  cur = conn.cursor()
  cur.execute('SELECT * FROM notes ORDER BY id DESC LIMIT ?', (limit,))
  for row in cur.fetchall():
    yield Note(**row)


def get_note(conn: sqlite3.Connection, note_id: int) -> Optional[Note]:
  cur = conn.cursor()
  cur.execute('SELECT * FROM notes WHERE id = ?', (note_id,))
  row = cur.fetchone()
  return Note(**row) if row else None


def delete_note(conn: sqlite3.Connection, note_id: int) -> bool:
  cur = conn.cursor()
  cur.execute('DELETE FROM notes WHERE id = ?', (note_id,))
  conn.commit()
  return cur.rowcount > 0


def top_tags(
  conn: sqlite3.Connection, limit: int = 20
) -> Iterable[Tuple[str, int]]:
  cur = conn.cursor()
  cur.execute('SELECT tags FROM notes;')
  counts: dict[str, int] = {}
  for (tag_str,) in cur.fetchall():
    for t in tag_str.split(','):
      t = t.strip()
      if t:
        counts[t] = counts.get(t, 0) + 1
  return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]


def search_notes(
  conn: sqlite3.Connection,
  query: str,
  project: Optional[str] = None,
  since: Optional[str] = None,
  until: Optional[str] = None,
  limit: int = 50,
) -> List[Note]:
  cur = conn.cursor()
  clauses = []
  params: list = []

  # Decide search backend
  if query and has_fts5(conn):
    clauses.append(
      'rowid IN (SELECT rowid FROM notes_fts WHERE notes_fts MATCH ?)'
    )
    params.append(query)
  elif query:
    clauses.append('(text LIKE ? OR tags LIKE ?)')
    like = f'%{query}%'
    params.extend([like, like])
  else:
    # no query: select all
    pass

  if project:
    clauses.append('project = ?')
    params.append(project)

  if since:
    clauses.append('created_at >= ?')
    params.append(since)

  if until:
    clauses.append('created_at <= ?')
    params.append(until)

  where = ' AND '.join(clauses) if clauses else '1=1'
  sql = f'SELECT * FROM notes WHERE {where} ORDER BY id DESC LIMIT ?'
  params.append(limit)
  cur.execute(sql, params)
  return [Note(**row) for row in cur.fetchall()]
