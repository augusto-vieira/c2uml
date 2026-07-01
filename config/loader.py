import os
import re
import fnmatch
import yaml


_DEFAULTS = {
    "include_dirs": [],
    "packages": {
        "markers": ["lib", "include", "src", "public", "private"],
        "groups": ["builtin", "optionals", "modules", "drivers", "core", "plugins"],
        "rules": [],
    },
    "visibility": {
        "public": ["include/public/"],
        "private": ["include/private/"],
    },
    "exclude": ["*/samples/*", "*/tests/*", "*/test/*", "*/examples/*"],
}


class Config:
    def __init__(self, data=None):
        data = data or {}
        self.include_dirs = data.get("include_dirs", _DEFAULTS["include_dirs"])

        pkg = data.get("packages", {})
        self.package_markers = pkg.get("markers", _DEFAULTS["packages"]["markers"])
        self.package_groups = pkg.get("groups", _DEFAULTS["packages"]["groups"])
        self.package_rules = pkg.get("rules", _DEFAULTS["packages"]["rules"])

        vis = data.get("visibility", {})
        self.visibility_public = vis.get("public", _DEFAULTS["visibility"]["public"])
        self.visibility_private = vis.get("private", _DEFAULTS["visibility"]["private"])

        self.exclude = _DEFAULTS["exclude"] + data.get("exclude", [])

    def infer_package(self, file_path):
        norm = os.path.normpath(file_path)
        for rule in self.package_rules:
            if fnmatch.fnmatch(norm, rule["pattern"]):
                return rule["name"]
        parts = norm.split(os.sep)
        for i, p in enumerate(parts):
            if p in self.package_markers and i > 0:
                return parts[i - 1]
        # Fallback: use parent directory name for flat projects
        parent = os.path.basename(os.path.dirname(norm))
        if parent and parent != '.':
            return parent
        return None

    def infer_group(self, file_path):
        parts = os.path.normpath(file_path).split(os.sep)
        group = None
        for p in parts:
            if p in self.package_groups:
                group = p
        return group

    def infer_visibility(self, file_path):
        norm = os.path.normpath(file_path)
        for pat in self.visibility_private:
            if pat.replace("/", os.sep) in norm:
                return "-"
        return "+"

    def is_excluded(self, file_path):
        norm = os.path.normpath(file_path)
        basename = os.path.basename(norm)
        for pat in self.exclude:
            if fnmatch.fnmatch(basename, pat) or fnmatch.fnmatch(norm, pat):
                return True
            if pat.endswith('*') and pat.startswith('*'):
                mid = pat.strip('*').replace('/', os.sep)
                if mid in norm:
                    return True
        return False


def load_config(input_path):
    search = input_path if os.path.isdir(input_path) else os.path.dirname(input_path)
    for name in (".c2uml.yaml", ".c2uml.yml"):
        path = os.path.join(search, name)
        if os.path.isfile(path):
            with open(path) as f:
                return Config(yaml.safe_load(f) or {})
    return Config()
