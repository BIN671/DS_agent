#from pip._internal.utils import subprocess
import subprocess
import os


def bash(cwd: str | None = None):
    def run(cmd: str, timeout_s: int = 60):
        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                #executable="cmd.exe",
                cwd=cwd if cwd else None,
                capture_output=True,
                text=True,
                encoding="cp866",
                errors="replace",
                timeout=timeout_s, )
            return f"returncode: {proc.returncode}\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
        except subprocess.TimeoutExpired as e:
            return f"{str(e)}\nstdout: {e.stdout}\nstderr: {e.stderr}"

    return run


def read(cwd: str | None = None):
    def run(path: str):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"{str(e)}\nstdout: {e.stdout}\nstderr: {e.stderr}"

    return run


def write(cwd: str | None = None):
    def run(path: str, content: str, splt: str = "w"):
        try:
            if cwd:
                full_path = os.path.join(cwd, path)
            else:
                full_path = path

            # Создаем папки, если их нет
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            if "a" == splt:
                with open(full_path, "a", encoding="utf-8") as f:
                    f.write(content)


            elif "w" == splt:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)


            else:
                if splt.startswith(":"):
                    bound = int(splt[1:])
                    with open(full_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    if not content.endswith("\n"):
                        content += "\n"
                    lines[:bound] = [content]
                    with open(full_path, "w", encoding='utf-8') as f:
                        f.writelines(lines)


                elif splt.endswith(":"):
                    bound = int(splt[:-1])
                    with open(full_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    if not content.endswith("\n"):
                        content += "\n"
                    lines[bound:] = [content]
                    with open(full_path, "w", encoding='utf-8') as f:
                        f.writelines(lines)


                else:
                    bounds = tuple(map(int, splt.split(":")))
                    with open(full_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    if not content.endswith("\n"):
                        content += "\n"
                    lines[bounds[0]:bounds[1]] = [content]
                    with open(full_path, "w", encoding='utf-8') as f:
                        f.writelines(lines)
            return f"Файл {full_path} успешно записан"

        except Exception as e:
            return f"{str(e)}\nstdout: {e.stdout}\nstderr: {e.stderr}"

    return run


executors_table = {
    "bash": bash,
    "read": read,
    "write": write
}
