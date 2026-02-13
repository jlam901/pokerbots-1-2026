from pathlib import Path
import importlib.util
import os
import sys


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    local_dir = Path(__file__).resolve().parent

    sys.path.insert(0, str(local_dir))
    os.chdir(repo_root)

    engine_path = repo_root / "engine.py"
    spec = importlib.util.spec_from_file_location("engine", engine_path)
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)

    engine.Game().run()


if __name__ == "__main__":
    main()
