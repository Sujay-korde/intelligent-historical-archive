import sys
import subprocess

def win_to_wsl(path: str) -> str:
    if len(path) >= 2 and path[1] == ":" and path[0].isalpha():
        drive = path[0].lower()
        rest = path[2:].replace("\\", "/")
        return f"/mnt/{drive}{rest}"
    return path.replace("\\", "/")

def main():
    args = [win_to_wsl(a) for a in sys.argv[1:]]
    cmd = ["wsl", "-d", "Ubuntu", "--", "tesseract"] + args
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    sys.stdout.buffer.write(proc.stdout)
    sys.stderr.buffer.write(proc.stderr)
    sys.exit(proc.returncode)

if __name__ == "__main__":
    main()
