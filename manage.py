"""Cross-platform entry point; all processes run locally without a shell."""

import argparse
import os
import shutil
import signal
import subprocess
import time
import venv
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"
PYTHON = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def npm() -> str:
    executable = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if executable is None:
        raise SystemExit(
            "Node.js et npm sont requis. Installez Node.js 22.18+ ou 24 LTS."
        )
    return executable


def run(args: list[str], cwd: Path = ROOT) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def install() -> None:
    if not PYTHON.exists():
        venv.create(ROOT / ".venv", with_pip=True)
    run([str(PYTHON), "-m", "pip", "install", "-e", str(ROOT / "backend") + "[dev]"])
    run(
        [npm(), "ci" if (FRONTEND / "package-lock.json").exists() else "install"],
        FRONTEND,
    )


def serve(*, development: bool) -> None:
    if not development and not (FRONTEND / "dist" / "index.html").exists():
        raise SystemExit("Construisez d'abord le frontend : make build.")
    commands = [
        [
            str(PYTHON),
            "-m",
            "uvicorn",
            "santa.app:create_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
            "--no-access-log",
        ]
    ]
    if development:
        node = shutil.which("node")
        if node is None:
            raise SystemExit("Node.js est requis.")
        commands.append(
            [node, str(FRONTEND / "node_modules" / "vite" / "bin" / "vite.js")]
        )
    processes: list[subprocess.Popen] = []
    stopping = False

    def interrupt(_signum, _frame) -> None:
        nonlocal stopping
        stopping = True

    previous_handler = signal.signal(signal.SIGINT, interrupt)
    try:
        for command in commands:
            options = (
                {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
                if os.name == "nt"
                else {}
            )
            processes.append(
                subprocess.Popen(
                    command,
                    cwd=FRONTEND if command == commands[-1] and development else ROOT,
                    **options,
                )
            )
        urls = ["http://127.0.0.1:8000/api/health"]
        if development:
            urls.append("http://127.0.0.1:5173")
        deadline = time.monotonic() + 30
        for url in urls:
            while not stopping:
                if any(process.poll() is not None for process in processes):
                    raise SystemExit(
                        "Un service s'est arrêté au démarrage. Consultez l'erreur ci-dessus."
                    )
                try:
                    with urlopen(url, timeout=1) as response:
                        if response.status == 200:
                            break
                except (URLError, TimeoutError):
                    if time.monotonic() >= deadline:
                        raise SystemExit(f"Le service ne répond pas : {url}") from None
                    time.sleep(0.25)
        if not stopping:
            print(
                "\nSecret Santa : http://127.0.0.1:"
                + ("5173" if development else "8000")
                + "\nCtrl+C pour arrêter les services.",
                flush=True,
            )
        while not stopping:
            for process in processes:
                if process.poll() is not None:
                    raise SystemExit(
                        f"Un service s'est arrêté (code {process.returncode})."
                    )
            time.sleep(0.3)
    finally:
        for process in processes:
            if process.poll() is None:
                if os.name == "nt":
                    process.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    process.terminate()
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        signal.signal(signal.SIGINT, previous_handler)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["help", "install", "dev", "test", "build", "start", "lint"],
        default="help",
        nargs="?",
    )
    command = parser.parse_args().command
    if command == "help":
        print(
            "make install | dev | test | build | start | lint\n"
            "Sans make : python manage.py <commande>"
        )
        return
    if command == "install":
        install()
        return
    if not PYTHON.exists():
        raise SystemExit(
            "Dépendances absentes. Exécutez d'abord : python manage.py install"
        )
    if command in ("dev", "start"):
        serve(development=command == "dev")
    elif command == "test":
        run([str(PYTHON), "-m", "pytest"], ROOT / "backend")
        run([npm(), "test"], FRONTEND)
    elif command == "build":
        run([npm(), "run", "build"], FRONTEND)
    elif command == "lint":
        run([str(PYTHON), "-m", "ruff", "check", "backend", "manage.py"])
        run([npm(), "run", "lint"], FRONTEND)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode) from None
