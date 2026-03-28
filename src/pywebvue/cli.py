"""PyWebVue CLI - scaffold new projects from templates."""

from __future__ import annotations

import argparse
import keyword
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml
from loguru import logger

TEMPLATE_DIR = Path(__file__).parent / "templates" / "project"

# Matches {{UPPER_CASE}} placeholders only (not Vue {{ camelCase }} expressions)
_UNSUBSTITUTED_PATTERN = re.compile(r"\{\{[A-Z_][A-Z0-9_]*\}\}")


def _pascal_case(name: str) -> str:
    """Convert snake_case name to PascalCase."""
    return "".join(w.capitalize() for w in name.split("_"))


def _substitute(content: str, variables: dict[str, str]) -> str:
    """Replace {{KEY}} placeholders with values."""
    for key, value in variables.items():
        content = content.replace(f"{{{{{key}}}}}", value)
    return content


def _check_unsubstituted(content: str) -> list[str]:
    """Return list of unsubstituted {{UPPER_CASE}} placeholders found in content."""
    return _UNSUBSTITUTED_PATTERN.findall(content)


def _validate_project_name(name: str) -> tuple[bool, str]:
    """Check that project_name is a valid Python identifier and safe directory name."""
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
        return False, "Project name must be a valid Python identifier (letters, digits, underscores)"
    if keyword.iskeyword(name):
        return False, f"'{name}' is a Python keyword and cannot be used"
    return True, ""


def _run_command(cmd: list[str], cwd: Path, check: bool = False) -> bool:
    """Run a shell command and log the result.

    Returns True on success, False on failure.
    If check=True, exits on failure.
    """
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
            if check:
                sys.exit(1)
            return False
        else:
            logger.info("Command completed successfully")
            return True
    except FileNotFoundError:
        logger.warning(f"Command not found: {cmd[0]}")
        if check:
            sys.exit(1)
        return False
    except subprocess.TimeoutExpired:
        logger.warning(f"Command timed out: {' '.join(cmd)}")
        if check:
            sys.exit(1)
        return False


def create_project(args: argparse.Namespace) -> None:
    """Scaffold a new PyWebVue project from templates."""
    project_name: str = args.project_name
    title: str = args.title or project_name.replace("_", " ").title()
    width: int = args.width
    height: int = args.height
    force: bool = args.force

    # Validate project name
    valid, reason = _validate_project_name(project_name)
    if not valid:
        logger.error(reason)
        sys.exit(1)

    # Check target directory
    target_dir = Path.cwd() / project_name
    if target_dir.exists():
        if not force:
            logger.error(f"Directory already exists: {target_dir}")
            logger.error("Use --force to overwrite (with confirmation)")
            sys.exit(1)
        confirm = input(f"Overwrite {target_dir}? [y/N] ").strip().lower()
        if confirm != "y":
            logger.info("Aborted.")
            sys.exit(0)
        logger.info(f"Removing existing directory: {target_dir}")
        shutil.rmtree(target_dir)

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

        # Substitute {{VARIABLES}} in the destination filename
        dest_name = _substitute(dest_file.name, variables)
        if dest_name != dest_file.name:
            dest_file = dest_file.with_name(dest_name)

        # Ensure parent directory exists
        dest_file.parent.mkdir(parents=True, exist_ok=True)

        if src_file.name.endswith(".tpl"):
            # Template file: read, substitute, write
            content = src_file.read_text(encoding="utf-8")
            content = _substitute(content, variables)

            # Warn about unsubstituted placeholders
            unreplaced = _check_unsubstituted(content)
            for placeholder in unreplaced:
                logger.warning(
                    f"  Unsubstituted placeholder {placeholder} in {dest_file.name}"
                )

            dest_file.write_text(content, encoding="utf-8")
            logger.info(f"  Created: {dest_file.relative_to(target_dir)}")
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
    logger.info(f"  uv run python main.py          # Run with Vite dev mode")
    logger.info(f"  uv run pywebvue build           # Package for distribution")


def build_project(args: argparse.Namespace) -> None:
    """Build a PyWebVue project using PyInstaller."""
    project_dir = Path.cwd()

    # Discover project name from config.yaml or directory name
    config_path = project_dir / "config.yaml"
    if config_path.is_file():
        with open(config_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        project_name = cfg.get("app", {}).get("name", project_dir.name)
    else:
        project_name = project_dir.name

    # Step 0: Clean build directories if requested
    if args.clean:
        build_dir = project_dir / "build"
        dist_dir = project_dir / "dist"
        for d in (build_dir, dist_dir):
            if d.is_dir():
                logger.info(f"Cleaning directory: {d}")
                shutil.rmtree(d, ignore_errors=True)

    # Step 1: Build frontend
    if not args.skip_frontend:
        frontend_dir = project_dir / "frontend"
        if not frontend_dir.is_dir():
            logger.error(f"Frontend directory not found: {frontend_dir}")
            logger.error("Run this command from the project root directory.")
            sys.exit(1)
        logger.info("Building frontend...")
        _run_command(["bun", "run", "build"], frontend_dir, check=True)
    else:
        logger.info("Skipping frontend build (--skip-frontend)")

    # Step 2: Select spec file
    spec_file: Path | None = args.spec

    if spec_file is None:
        mode = args.mode or "onedir"
        if mode == "onedir":
            spec_file = project_dir / f"{project_name}.spec"
        elif mode == "onefile":
            spec_file = project_dir / f"{project_name}-onefile.spec"
        elif mode == "debug":
            spec_file = project_dir / f"{project_name}-debug.spec"
        else:
            logger.error(f"Unknown build mode: {mode}")
            logger.error("Valid modes: onedir, onefile, debug")
            sys.exit(1)

    if not spec_file.is_file():
        logger.error(f"Spec file not found: {spec_file}")
        logger.error("Ensure you are in the project root directory.")
        sys.exit(1)

    # Step 3: Check PyInstaller availability
    if shutil.which("pyinstaller") is None:
        logger.error(
            "PyInstaller is not installed. Install it with: uv add --dev pyinstaller"
        )
        sys.exit(1)

    # Step 4: Run PyInstaller
    pyinstaller_cmd = ["pyinstaller", "--noconfirm"]

    # --icon override
    if args.icon:
        icon_path = Path(args.icon)
        if not icon_path.is_absolute():
            icon_path = project_dir / icon_path
        if not icon_path.is_file():
            logger.error(f"Icon file not found: {icon_path}")
            sys.exit(1)
        pyinstaller_cmd.extend(["--icon", str(icon_path)])

    # --output-dir override
    if args.output_dir:
        output_path = Path(args.output_dir)
        if not output_path.is_absolute():
            output_path = project_dir / output_path
        output_path.mkdir(parents=True, exist_ok=True)
        pyinstaller_cmd.extend(["--distpath", str(output_path / "dist"), "--workpath", str(output_path / "build")])

    pyinstaller_cmd.append(str(spec_file))

    logger.info(f"Running PyInstaller with spec: {spec_file.name}")
    _run_command(pyinstaller_cmd, project_dir, check=True)

    logger.info("Build complete.")


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
    create_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing project directory (with confirmation)",
    )
    create_parser.set_defaults(func=create_project)

    # build subcommand
    build_parser = subparsers.add_parser(
        "build",
        help="Build a PyWebVue project for distribution",
    )
    build_parser.add_argument(
        "--mode",
        choices=["onedir", "onefile", "debug"],
        default=None,
        help="Build mode: onedir (folder), onefile (single exe), debug (console) (default: onedir)",
    )
    build_parser.add_argument(
        "--spec",
        type=Path,
        default=None,
        help="Path to a custom .spec file (overrides --mode)",
    )
    build_parser.add_argument(
        "--skip-frontend",
        action="store_true",
        help="Skip the frontend build step",
    )
    build_parser.add_argument(
        "--icon",
        type=str,
        default=None,
        help="Override app icon path (.ico for Windows)",
    )
    build_parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove build/ and dist/ directories before building",
    )
    build_parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Custom output directory for PyInstaller artifacts",
    )
    build_parser.set_defaults(func=build_project)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
