#from pip._internal.utils import subprocess
import subprocess

def bash(cwd:str|None=None):
    def run(cmd:str, timeout_s: int = 60):
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
                timeout=timeout_s,)
            return f"returncode: {proc.returncode}\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
        except subprocess.TimeoutExpired as e:
            return f"{str(e)}\nstdout: {e.stdout}\nstderr: {e.stderr}"
    return run


def read():
    pass

def write():
    pass



executors_table = {
    "bash": bash,
    "read": read,
    "write": write
}