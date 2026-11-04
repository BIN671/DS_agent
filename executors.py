import subprocess
import os


def _safe_err(e) -> str:
    """Безопасно формирует текст ошибки (у исключений нет .stdout/.stderr)."""
    parts = [str(e)]
    out = getattr(e, "stdout", None)
    err = getattr(e, "stderr", None)
    if out:
        parts.append(f"stdout: {out}")
    if err:
        parts.append(f"stderr: {err}")
    return "\n".join(parts)


def _resolve_path(cwd: str | None, path: str) -> str:
    """Возвращает абсолютный путь и не даёт выйти за пределы cwd."""
    if cwd:
        base = os.path.abspath(cwd)
        full_path = os.path.abspath(os.path.join(base, path))
        if os.path.commonpath([base, full_path]) != base:
            raise PermissionError(f"Путь вне рабочей директории: {full_path}")
        return full_path
    return os.path.abspath(path)


def bash(cwd: str | None = None):
    def run(cmd: str, timeout_s: int = 60):
        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                cwd=cwd if cwd else None,
                capture_output=True,
                text=True,
                encoding="cp866",
                errors="replace",
                timeout=timeout_s,
            )
            return f"returncode: {proc.returncode}\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
        except subprocess.TimeoutExpired as e:
            return _safe_err(e)
        except Exception as e:
            return _safe_err(e)

    return run


def read(cwd: str | None = None):
    def run(path: str):
        try:
            full_path = _resolve_path(cwd, path)
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return _safe_err(e)

    return run


def write(cwd: str | None = None):
    def run(path: str, content: str, splt: str = "w"):
        try:
            full_path = _resolve_path(cwd, path)

            parent = os.path.dirname(full_path)
            if parent:
                os.makedirs(parent, exist_ok=True)

            if splt == "a":
                with open(full_path, "a", encoding="utf-8") as f:
                    f.write(content)

            elif splt == "w":
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)

            else:
                n, k = map(int, splt.split(":"))
                with open(full_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                total = len(lines)
                if n < 0:
                    n = total + n
                if k < 0:
                    k = total + k

                n = max(0, n)
                k = min(k, total - 1)

                if not content.endswith("\n"):
                    content += "\n"

                lines[n:k + 1] = [content]

                with open(full_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)

            return f"Файл {full_path} успешно записан"

        except Exception as e:
            return _safe_err(e)

    return run


def open_app(cwd: str | None = None):
    def run(cmd: str):
        try:

            subprocess.Popen(
                cmd,
                shell=True,
                cwd=cwd if cwd else None,

            )
            return f"Успешно: команда '{cmd}' отправлена на выполнение."
        except Exception as e:
            return f"Ошибка при запуске '{cmd}': {e}"

    return run

executors_table = {
    "bash": bash,
    "read": read,
    "write": write,
    "open_app": open_app
}
