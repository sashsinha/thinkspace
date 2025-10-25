from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional, Tuple


def _git(*args: str) -> Optional[str]:
  try:
    out = subprocess.check_output(['git', *args], stderr=subprocess.DEVNULL)
    return out.decode().strip()
  except Exception:
    return None


def detect_project(cwd: Optional[Path] = None) -> Tuple[str, Path]:
  """Determine a sensible project name and root based on Git;
  fall back to current directory name.
  """
  cwd = cwd or Path.cwd()
  toplevel = _git('rev-parse', '--show-toplevel')
  if toplevel:
    root = Path(toplevel)
    name = root.name
    return name, root

  # Fallback to nearest folder containing a project file
  for marker in ('.git', 'pyproject.toml', 'package.json', 'requirements.txt'):
    for p in [cwd, *cwd.resolve().parents]:
      if (p / marker).exists():
        return p.name, p

  # Final fallback: current dir
  return cwd.resolve().name, cwd.resolve()
