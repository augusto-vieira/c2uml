import os

_SKIP_DIRS = {"venv", ".venv", "env", ".git", "node_modules", "__pycache__", "build", "dist"}

def load_files(path):
    files = []
    if os.path.isfile(path):
        if path.endswith(".c") or path.endswith(".h"):
            return [path]
        return []

    for root, dirs, fs in os.walk(path):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for f in fs:
            if f.endswith(".c") or f.endswith(".h"):
                files.append(os.path.join(root, f))

    return files
