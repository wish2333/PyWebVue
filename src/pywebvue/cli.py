"""PyWebVue CLI - scaffold new projects from templates."""

from __future__ import annotations

import argparse
import shutil
import re
import subprocess
import sys
from pathlib import Path

from loguru import logger

TEMPLATE_DIR = Path(__file__).parent / "templates" / "project"


def _pascal_case(name: str) -> str:
    """Convert snake_case name to PascalCase."""
    return "".join(w.capitalize() for w in name.split("_"))


def _substitute(content: str, variables: dict[str, str]) -> str:
    """Replace {{KEY}} placeholders with values."""
    for key, value in variables.items():
        content = content.replace(f"{{{{{key}}}}}", value)
    return content


def _validate_project_name(name: str) -> tuple[bool, str]:
    """Check that project_name is a valid Python identifier and safe directory name."""
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
        return False, "Project name must be a valid Python identifier (letters, digits, underscores)"
    if keyword.iskeyword(name):
        return False, f"'{name}' is a Python keyword and cannot be used"
    return True, ""


import keyword


def _run_command(cmd: list[str], cwd: Path) -> None:
    """Run a shell command and log the result."""
    logger.info(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            logger.warning(f"Command failed (exit {result.returncode}): {result.stderr.strip()}")
        else:
            logger.info("Command completed successfully")
    except FileNotFoundError:
        logger.warning(f"Command not found: {cmd[0]}")
    except subprocess.TimeoutExpired:
        logger.warning(f"Command timed out: {' '.join(cmd)}")


def create_project(args: argparse.Namespace) -> None:
    """Scaffold a new PyWebVue project from templates."""
    project_name: str = args.project_name
    title: str = args.title or project_name.replace("_", " ").title()
    width: int = args.width
    height: int = args.height

    # Validate project name
    valid, reason = _validate_project_name(project_name)
    if not valid:
        logger.error(reason)
        sys.exit(1)

    # Check target directory
    target_dir = Path.cwd() / project_name
    if target_dir.exists():
        logger.error(f"Directory already exists: {target_dir}")
        sys.exit(1)

    # Compute template variables
    variables = {
        "PROJECT_NAME": project_name,
        "PROJECT_TITLE": title,
        "CLASS_NAME": _pascal_case(project_name),
        "WIDTH": str(width),
        "HEIGHT": str(height),
    }

    logger.info(f"Scaffolding project: {project_name}")
    logger.info(f"Title: {title}")
    logger.info(f"Window: {width}x{height}")

    # Walk template directory and process files
    for src_file in sorted(TEMPLATE_DIR.rglob("*")):
        if not src_file.is_file():
            continue

        rel_path = src_file.relative_to(TEMPLATE_DIR)
        dest_file = target_dir / rel_path

        # Strip .tpl suffix from destination filename
        if dest_file.name.endswith(".tpl"):
            dest_file = dest_file.with_name(dest_file.name[:-4])

        # Ensure parent directory exists
        dest_file.parent.mkdir(parents=True, exist_ok=True)

        if src_file.name.endswith(".tpl"):
            # Template file: read, substitute, write
            content = src_file.read_text(encoding="utf-8")
            content = _substitute(content, variables)
            dest_file.write_text(content, encoding="utf-8")
            logger.info(f"  Created: {rel_path.with_suffix(rel_path.suffix[:-4])}")
        else:
            # Static file: copy as-is
            shutil.copy2(src_file, dest_file)
            logger.info(f"  Copied:  {rel_path}")

    logger.info("Project scaffolded successfully.")

    # Run bun install in frontend directory
    frontend_dir = target_dir / "frontend"
    if frontend_dir.is_dir():
        bun_lock = frontend_dir / "bun.lockb"
        if not bun_lock.exists():
            logger.info("Installing frontend dependencies with bun...")
            _run_command(["bun", "install"], frontend_dir)
        else:
            logger.info("bun.lockb already exists, skipping bun install.")

    logger.info(f"\nNext steps:")
    logger.info(f"  cd {project_name}")
    logger.info(f"  uv run python main.py          # Run with production build")
    logger.info(f"  cd frontend && bun dev          # Start Vite dev server")
    logger.info(f"  cd frontend && bun run build    # Build for production")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="pywebvue",
        description="PyWebVue - Desktop rapid development framework CLI",
    )
    subparsers = parser.add_subparsers(dest="command")

    # create subcommand
    create_parser = subparsers.add_parser(
        "create",
        help="Scaffold a new PyWebVue project",
    )
    create_parser.add_argument(
        "project_name",
        help="Project name (snake_case, used as Python module name)",
    )
    create_parser.add_argument(
        "--title",
        default="",
        help="Application window title (default: derived from project_name)",
    )
    create_parser.add_argument(
        "--width",
        type=int,
        default=900,
        help="Window width in pixels (default: 900)",
    )
    create_parser.add_argument(
        "--height",
        type=int,
        default=650,
        help="Window height in pixels (default: 650)",
    )
    create_parser.set_defaults(func=create_project)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
