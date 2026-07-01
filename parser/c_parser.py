import os
import re
import shutil

from pycparser import parse_file, CParser

_TYPE_STUBS = (
    "typedef int bool;\n"
    "typedef unsigned char uint8_t;\n"
    "typedef unsigned short uint16_t;\n"
    "typedef unsigned int uint32_t;\n"
    "typedef unsigned long long uint64_t;\n"
    "typedef signed char int8_t;\n"
    "typedef signed short int16_t;\n"
    "typedef signed int int32_t;\n"
    "typedef signed long long int64_t;\n"
    "typedef unsigned long size_t;\n"
    "typedef long ssize_t;\n"
    "typedef void* va_list;\n"
    "typedef long time_t;\n"
    "typedef long off_t;\n"
    "typedef int pid_t;\n"
    "typedef unsigned int uid_t;\n"
    "typedef unsigned int gid_t;\n"
    "typedef unsigned int mode_t;\n"
    "typedef int socklen_t;\n"
    "typedef unsigned short sa_family_t;\n"
    "struct sockaddr { sa_family_t sa_family; char sa_data[14]; };\n"
)


_SKIP_DIRS = {"venv", ".venv", "env", ".git", "node_modules", "__pycache__", "build", "dist"}


def collect_include_dirs(base_path):
    dirs = []
    for root, subdirs, _ in os.walk(base_path):
        subdirs[:] = [d for d in subdirs if d not in _SKIP_DIRS]
        for d in subdirs:
            if d == "include":
                inc = os.path.join(root, d)
                dirs.append(inc)
                for sub in os.listdir(inc):
                    full = os.path.join(inc, sub)
                    if os.path.isdir(full):
                        dirs.append(full)
    return dirs


def parse_c_file(file_path, include_dirs=None, quiet=False):
    import pycparser
    fake_libc = os.path.join(os.path.dirname(pycparser.__file__), "utils", "fake_libc_include")

    cpp_path = shutil.which("cpp") or shutil.which("gcc")
    if cpp_path:
        cpp_args = ["-E"]
        if os.path.isdir(fake_libc):
            cpp_args += ["-I", fake_libc]
        for inc in (include_dirs or []):
            cpp_args += ["-I", inc]
        try:
            import subprocess
            stderr = subprocess.DEVNULL if quiet else None
            return parse_file(file_path, use_cpp=True, cpp_path=cpp_path,
                              cpp_args=cpp_args + (['-w'] if quiet else []))
        except Exception:
            return _parse_without_cpp(file_path)

    return _parse_without_cpp(file_path)


def extract_project_includes(file_path, all_headers):
    header_basenames = {os.path.basename(h) for h in all_headers}
    deps = []
    try:
        with open(file_path, "r") as f:
            for line in f:
                m = re.match(r'\s*#include\s*[<"]([^>"]+)[>"]', line)
                if m and m.group(1) in header_basenames:
                    deps.append(m.group(1))
    except Exception:
        pass
    return deps


_MACRO_FUNC_RE = re.compile(
    r'^\s*#define\s+([a-z][a-zA-Z0-9_]*)\s*\(([^)]*)\)',
    re.MULTILINE,
)
_MACRO_CONST_RE = re.compile(
    r'^\s*#define\s+([A-Z][A-Z0-9_]+)\s+(.+?)\s*$',
    re.MULTILINE,
)
_HEADER_GUARD_RE = re.compile(r'^[A-Z_]+_H_?$')


def extract_macros(file_path):
    from domain.models import MacroModel
    macros = []
    try:
        with open(file_path, "r") as f:
            code = f.read()
    except Exception:
        return macros

    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    code = re.sub(r'//[^\n]*', '', code)

    for m in _MACRO_FUNC_RE.finditer(code):
        name = m.group(1)
        params = [p.strip() for p in m.group(2).split(",") if p.strip()]
        macros.append(MacroModel(name=name, parameters=params, is_function=True, file=file_path))

    for m in _MACRO_CONST_RE.finditer(code):
        name = m.group(1)
        value = m.group(2).rstrip("\\")
        if _HEADER_GUARD_RE.match(name):
            continue
        macros.append(MacroModel(name=name, value=value.strip(), is_function=False, file=file_path))

    return macros


def _strip_comments(code):
    # Remove C block comments /* ... */ and line comments // ...
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    code = re.sub(r'//[^\n]*', '', code)
    return code


def _strip_preprocessor(code):
    # Remove preprocessor directives (including multi-line with backslash continuation)
    code = re.sub(r'^\s*#(?:.*\\\n)*.*$', '', code, flags=re.MULTILINE)
    return code


def _collect_unknown_types(code, known_types):
    """Scan for typedef references and struct field types that aren't known."""
    # Match identifiers used as types (before * or identifier)
    type_pattern = re.compile(r'\b([a-zA-Z_]\w+_t)\b')
    found = set(type_pattern.findall(code))
    return found - known_types


def _parse_without_cpp(file_path):
    with open(file_path, "r") as f:
        code = f.read()

    code = _strip_comments(code)
    code = _strip_preprocessor(code)

    code = re.sub(r'__attribute__\s*\(\(.*?\)\)', '', code, flags=re.DOTALL)

    # Remove function bodies to allow parsing .c files
    code = _strip_function_bodies(code)

    known = {
        "bool", "uint8_t", "uint16_t", "uint32_t", "uint64_t",
        "int8_t", "int16_t", "int32_t", "int64_t", "size_t", "ssize_t",
        "va_list", "time_t", "off_t", "pid_t", "uid_t", "gid_t",
        "mode_t", "socklen_t", "sa_family_t",
    }

    unknown = _collect_unknown_types(code, known)
    extra_stubs = "\n".join(f"typedef int {t};" for t in sorted(unknown))

    full_code = _TYPE_STUBS + extra_stubs + "\n" + code

    parser = CParser()
    return parser.parse(full_code, filename=file_path)


def _strip_function_bodies(code):
    result = []
    depth = 0
    i = 0
    in_body = False
    while i < len(code):
        ch = code[i]
        if ch == '{' and depth == 0:
            # Check if this is a struct/union/enum definition or a function body
            preceding = code[:i].rstrip()
            if re.search(r'\)\s*$', preceding):
                in_body = True
                result.append(';')
            else:
                result.append(ch)
            depth += 1
        elif ch == '{':
            depth += 1
            if not in_body:
                result.append(ch)
        elif ch == '}':
            depth -= 1
            if depth == 0 and in_body:
                in_body = False
            elif not in_body:
                result.append(ch)
        elif not in_body:
            result.append(ch)
        i += 1
    return ''.join(result)


_ADD_LIBRARY_RE = re.compile(
    r'add_library\s*\(\s*(\S+)',
    re.IGNORECASE,
)
_TARGET_LINK_RE = re.compile(
    r'target_link_libraries\s*\(\s*(\S+)(.*?)\)',
    re.DOTALL | re.IGNORECASE,
)
_CMAKE_KEYWORDS = {'PUBLIC', 'PRIVATE', 'INTERFACE'}


def extract_cmake_deps(base_path):
    targets = set()
    deps = {}
    for root, _, filenames in os.walk(base_path):
        for fn in filenames:
            if fn != 'CMakeLists.txt':
                continue
            path = os.path.join(root, fn)
            try:
                with open(path) as f:
                    content = f.read()
            except Exception:
                continue
            for m in _ADD_LIBRARY_RE.finditer(content):
                targets.add(m.group(1))
            for m in _TARGET_LINK_RE.finditer(content):
                target = m.group(1)
                body = m.group(2)
                libs = [t for t in body.split() if t not in _CMAKE_KEYWORDS]
                if libs:
                    deps.setdefault(target, set()).update(libs)
    return targets, deps


_FUNC_CALL_RE = re.compile(r'\b([a-zA-Z_]\w+)\s*\(')
_IGNORE_CALLS = {
    'if', 'for', 'while', 'switch', 'return', 'sizeof', 'typeof',
    'printf', 'fprintf', 'sprintf', 'snprintf', 'memcpy', 'memset',
    'malloc', 'calloc', 'realloc', 'free', 'strlen', 'strcmp', 'strncmp',
    'strcpy', 'strncpy', 'strcat', 'strncat', 'atoi', 'atof',
    'fopen', 'fclose', 'fread', 'fwrite', 'fgets', 'fputs',
}


def extract_function_calls(file_path):
    try:
        with open(file_path, "r") as f:
            code = f.read()
    except Exception:
        return []

    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    code = re.sub(r'//[^\n]*', '', code)

    calls = set()
    for m in _FUNC_CALL_RE.finditer(code):
        name = m.group(1)
        if name not in _IGNORE_CALLS and not name.startswith('__'):
            calls.add(name)
    return list(calls)
