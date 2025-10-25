from __future__ import annotations

from contextlib import closing

from typer.testing import CliRunner

from thinkspace import cli as cli_module
from thinkspace.storage import connect, get_note, iter_recent


def test_cli_note_creates_note_and_tags(
  scoped_db, cli_runner: CliRunner, monkeypatch
):
  monkeypatch.setattr(cli_module, 'detect_project', lambda: ('demo', scoped_db))
  monkeypatch.setattr(
    cli_module, '_auto_time_tags', lambda dt=None: ['y:2024', 'ym:2024-01']
  )

  result = cli_runner.invoke(cli_module.app, ['note', 'hello', 'world'])
  assert result.exit_code == 0
  assert 'Saved note' in result.stdout

  with closing(connect()) as conn:
    recent = list(iter_recent(conn, limit=1))
    assert recent, 'note command should persist a record'
    note = recent[0]
    assert note.text == 'hello world'
    tags = set(note.tags.split(','))
    assert 'project:demo' in tags
    assert 'y:2024' in tags


def test_cli_delete_confirmation_flow(
  scoped_db, cli_runner: CliRunner, insert_sample, monkeypatch
):
  monkeypatch.setattr(cli_module, 'detect_project', lambda: ('demo', scoped_db))
  with closing(connect()) as conn:
    nid = insert_sample(conn, 'temp note to delete')

  decline = cli_runner.invoke(cli_module.app, ['delete', str(nid)], input='n\n')
  assert decline.exit_code == 0
  assert 'Delete note #' in decline.stdout
  assert 'Skipped note' in decline.stdout
  with closing(connect()) as conn:
    assert get_note(conn, nid) is not None

  confirm = cli_runner.invoke(cli_module.app, ['delete', str(nid), '--yes'])
  assert confirm.exit_code == 0
  assert 'Deleted note' in confirm.stdout
  with closing(connect()) as conn:
    assert get_note(conn, nid) is None
