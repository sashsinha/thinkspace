from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import __version__
from .context import detect_project
from .storage import (
  connect,
  db_path,
  delete_note,
  get_note,
  insert_note,
  iter_recent,
  search_notes,
  top_tags,
)

app = typer.Typer(
  add_completion=True,
  help='🧠 thinkspace — Context‑Aware Scratchpad for Coders',
)

console = Console()


def _auto_time_tags(dt: Optional[datetime] = None) -> list[str]:
  dt = dt or datetime.now(timezone.utc)
  return [
    f'y:{dt:%Y}',
    f'ym:{dt:%Y-%m}',
    f'ymd:{dt:%Y-%m-%d}',
  ]


def _project_tag(name: str) -> str:
  return f'project:{name}'


def _escape(s: str) -> str:
  # Rich markup uses square brackets for control sequences; escape user input
  return s.replace('[', r'\[').replace(']', r'\]')


def _format_snippet(text: str, max_len: int = 60) -> str:
  snippet = text.strip().replace('\n', ' ')
  if len(snippet) > max_len:
    return snippet[: max_len - 1] + '…'
  return snippet


def _interactive_select_notes(conn, *, limit: int) -> list[int]:
  notes = list(iter_recent(conn, limit=limit))
  if not notes:
    console.print('[dim]No recent notes to choose from.[/]')
    return []

  available = {n.id: n for n in notes}
  selected: set[int] = set()

  while True:
    table = Table(title='🗂️ Select notes to delete', box=box.SIMPLE_HEAVY)
    table.add_column('Pick', justify='center', style='cyan')
    table.add_column('ID', justify='right', style='dim')
    table.add_column('Snippet')
    table.add_column('Project', style='cyan')
    table.add_column('When', style='yellow')

    for n in notes:
      mark = '[x]' if n.id in selected else '[ ]'
      table.add_row(
        mark, str(n.id), _format_snippet(n.text, 60), n.project, n.created_at
      )

    console.print(table)
    console.print(
      '[dim]Toggle selections by entering note IDs separated by spaces or commas.[/]'
    )
    console.print("[dim]Press Enter to confirm, or type 'q' to cancel.[/]")

    try:
      raw = console.input('[cyan]select> [/cyan]').strip()
    except (EOFError, KeyboardInterrupt):
      console.print('[dim]Selection cancelled.[/]')
      return []

    if raw.lower() in {'q', 'quit'}:
      console.print('[dim]Selection cancelled.[/]')
      return []

    if not raw:
      if selected:
        return [n.id for n in notes if n.id in selected]
      console.print('[yellow]No notes selected yet.[/]')
      continue

    tokens = [tok for tok in re.split(r'[,\s]+', raw) if tok]
    invalid: list[str] = []
    for tok in tokens:
      try:
        nid = int(tok)
      except ValueError:
        invalid.append(tok)
        continue
      if nid not in available:
        invalid.append(tok)
        continue
      if nid in selected:
        selected.remove(nid)
      else:
        selected.add(nid)

    if invalid:
      console.print(f'[yellow]Ignored: {", ".join(invalid)}[/]')

    console.print()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
  if ctx.invoked_subcommand is None:
    console.print(
      Panel.fit(
        Text.from_markup(
          '[bold]🧠 thinkspace[/bold]\n'
          'A tiny, blazing‑fast CLI scratchpad for devs.\n'
          '[dim]Use[/dim] [bold]thinkspace note "..."[/bold] [dim]or[/dim] [bold]thinkspace search "..."[/bold]'
        ),
        title='Welcome',
        border_style='cyan',
      )
    )
    console.print('[dim]Version[/dim] ', __version__)


@app.command(help='✍️  Capture a quick note. Auto‑tags by project and time.')
def note(
  text: List[str] = typer.Argument(
    ..., help='The note text, quoted if it has spaces.'
  ),
  tag: List[str] = typer.Option(
    None, '--tag', '-t', help='Optional manual tag(s). Repeat for multiple.'
  ),
):
  full_text = ' '.join(text).strip()
  if not full_text:
    raise typer.BadParameter('Note text cannot be empty.')

  project_name, project_root = detect_project()
  tags = [_project_tag(project_name), *_auto_time_tags()]
  if tag:
    tags.extend(tag)

  conn = connect()
  new_id = insert_note(conn, full_text, project_name, tags, Path.cwd())

  tags_str = ', '.join(tags)
  console.print(
    Panel.fit(
      f'✍️  [bold]Saved note #[/bold]{new_id}\n\n'
      f'[bold]Project:[/bold] {_escape(project_name)}\n'
      f'[bold]Tags:[/bold] {tags_str}\n\n'
      f'[italic]{_escape(full_text)}[/]',
      title='thinkspace',
      border_style='green',
    )
  )


@app.command(help='🔎  Search notes by text and optional filters.')
def search(
  query: List[str] = typer.Argument(..., help='Search query'),
  project: Optional[str] = typer.Option(
    None, '--project', '-p', help='Project name filter'
  ),
  since: Optional[str] = typer.Option(
    None, help='ISO date lower bound (e.g. 2025-01-01)'
  ),
  until: Optional[str] = typer.Option(
    None, help='ISO date upper bound (e.g. 2025-12-31)'
  ),
  limit: int = typer.Option(50, help='Max results'),
):
  q = ' '.join(query).strip()
  if not q:
    raise typer.BadParameter('Query cannot be empty.')

  conn = connect()
  rows = search_notes(
    conn, q, project=project, since=since, until=until, limit=limit
  )

  if not rows:
    console.print('🙈 No matches.')
    raise typer.Exit()

  table = Table(title='🔎 Results', box=box.SIMPLE_HEAVY)
  table.add_column('ID', justify='right', style='dim')
  table.add_column('Snippet')
  table.add_column('Project', style='cyan')
  table.add_column('Tags', style='magenta')
  table.add_column('When', style='yellow')

  pattern = re.compile('|'.join(re.escape(t) for t in q.split()), re.IGNORECASE)
  for n in rows:
    snippet = n.text.strip().replace('\n', ' ')
    if len(snippet) > 120:
      snippet = snippet[:117] + '…'

    def high(m):
      return f'[reverse]{m.group(0)}[/reverse]'

    try:
      snippet_hl = pattern.sub(high, snippet)
    except re.error:
      snippet_hl = snippet

    table.add_row(str(n.id), snippet_hl, n.project, n.tags, n.created_at)

  console.print(table)


@app.command(name='list', help='🧾  List most recent notes.')
def list_notes(
  limit: int = typer.Option(20, help='How many notes to show'),
):
  conn = connect()
  table = Table(title='🧾 Recent notes', box=box.SIMPLE_HEAVY)
  table.add_column('ID', justify='right', style='dim')
  table.add_column('Text')
  table.add_column('Project', style='cyan')
  table.add_column('Tags', style='magenta')
  table.add_column('When', style='yellow')
  for n in iter_recent(conn, limit=limit):
    txt = n.text.strip().replace('\n', ' ')
    if len(txt) > 120:
      txt = txt[:117] + '…'
    table.add_row(str(n.id), txt, n.project, n.tags, n.created_at)
  console.print(table)


@app.command(help='🗑️  Delete note(s) by ID.')
def delete(
  note_id: List[int] = typer.Argument(
    None, help='One or more note IDs to delete.'
  ),
  yes: bool = typer.Option(
    False, '--yes', '-y', help='Skip confirmation prompt.'
  ),
  interactive: bool = typer.Option(
    False,
    '--interactive',
    '-i',
    help='Open an interactive picker for recent notes.',
  ),
  limit: int = typer.Option(
    20,
    '--limit',
    '-l',
    help='How many recent notes to show when using --interactive.',
  ),
):
  conn = connect()
  target_ids: list[int] = []

  if interactive:
    selected = _interactive_select_notes(conn, limit=limit)
    target_ids.extend(selected)

  if note_id:
    target_ids.extend(note_id)

  # Deduplicate while preserving order
  deduped: list[int] = []
  seen: set[int] = set()
  for nid in target_ids:
    if nid in seen:
      continue
    deduped.append(nid)
    seen.add(nid)

  if not deduped:
    console.print('[dim]No notes selected for deletion.[/]')
    return

  for nid in deduped:
    note = get_note(conn, nid)
    if not note:
      console.print(f'[yellow]Note #{nid} not found; skipping.[/]')
      continue

    snippet = _format_snippet(note.text, 60)

    if not yes:
      if not typer.confirm(
        f'Delete note #{nid}? Preview: {snippet}', default=False
      ):
        console.print(f'[dim]Skipped note #{nid}[/]')
        continue

    if delete_note(conn, nid):
      console.print(f'🗑️  Deleted note #{nid}.')
    else:
      console.print(f'[yellow]Note #{nid} could not be deleted.[/]')


@app.command(help='🏷️  Show top tags.')
def tags():
  conn = connect()
  tag_counts = top_tags(conn, limit=50)
  if not tag_counts:
    console.print(
      'No tags yet. Capture your first note with: [bold]thinkspace note "..."[/bold]'
    )
    raise typer.Exit()

  table = Table(title='🏷️ Top tags', box=box.SIMPLE_HEAVY)
  table.add_column('Tag', style='magenta')
  table.add_column('Count', justify='right', style='yellow')
  for tag, count in tag_counts:
    table.add_row(tag, str(count))
  console.print(table)


@app.command(help='📂  Print the database path.')
def db_path_cmd():
  console.print(str(db_path()))


@app.command(help='📤  Export notes to Markdown.')
def export(
  out: Path = typer.Option(
    Path('thinkspace-notes.md'), '--out', '-o', help='Output Markdown file path'
  ),
  project: Optional[str] = typer.Option(
    None, '--project', '-p', help='Filter by project'
  ),
):
  conn = connect()
  rows = search_notes(conn, query='', project=project, limit=10_000)
  if not rows:
    from .storage import iter_recent

    rows = list(iter_recent(conn, limit=10_000))

  lines = ['# 🧠 Thinkspace Export\n']
  for n in rows[::-1]:
    lines.append(f'## Note #{n.id}')
    lines.append(f'- **When:** {n.created_at}')
    lines.append(f'- **Project:** {n.project}')
    lines.append(f'- **Tags:** {n.tags}')
    lines.append('')
    lines.append(n.text)
    lines.append('')

  out.write_text('\n'.join(lines), encoding='utf-8')
  console.print(f'📤 Exported {len(rows)} notes → [bold]{out}[/bold]')


if __name__ == '__main__':
  app()
