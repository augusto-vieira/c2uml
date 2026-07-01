import argparse
import logging
import os
import shutil
import subprocess
import sys

from utils.file_loader import load_files
from parser.c_parser import parse_c_file, collect_include_dirs, extract_project_includes, extract_macros, extract_function_calls, extract_cmake_deps
from analyzer.model_builder import ModelBuilder
from generator.plantuml_generator import PlantUMLGenerator
from generator.viewer import generate_viewer_html
from generator.index import generate_index_html
from config.loader import load_config

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _build_models(files, include_dirs, config, quiet=False):
    all_structs = {}
    all_relations = []
    all_enums = {}
    all_callbacks = {}
    parsed = 0
    failed = 0

    devnull_fd = None
    old_stderr_fd = None
    if quiet:
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        old_stderr_fd = os.dup(2)
        os.dup2(devnull_fd, 2)

    for f in files:
        if config.is_excluded(f):
            continue
        try:
            ast = parse_c_file(f, include_dirs, quiet=quiet)
            builder = ModelBuilder(f)
            builder.visit(ast)
            structs, relations, enums, callbacks = builder.finalize()
            for name, s in structs.items():
                if name in all_structs:
                    existing = all_structs[name]
                    if existing.stereotype == "opaque" and s.stereotype != "opaque":
                        if existing.file.endswith(".h"):
                            s.file = existing.file
                        s.methods = existing.methods + [m for m in s.methods if m.name not in {em.name for em in existing.methods}]
                        all_structs[name] = s
                    else:
                        seen_methods = {m.name for m in existing.methods}
                        for m in s.methods:
                            if m.name not in seen_methods:
                                existing.methods.append(m)
                                seen_methods.add(m.name)
                        if not existing.attributes and s.attributes:
                            existing.attributes = s.attributes
                else:
                    all_structs[name] = s
            all_relations.extend(relations)
            all_enums.update(enums)
            all_callbacks.update(callbacks)
            parsed += 1
        except Exception as e:
            failed += 1

    if quiet:
        os.dup2(old_stderr_fd, 2)
        os.close(old_stderr_fd)
        os.close(devnull_fd)
        logger.info("Parsed %d/%d files (%d failed)", parsed, parsed + failed, failed)

    seen = set()
    unique = []
    for r in all_relations:
        key = (r.source, r.target, r.type)
        if key not in seen:
            seen.add(key)
            unique.append(r)

    return all_structs, unique, all_enums, all_callbacks


def _build_include_deps(files, config):
    header_files = [f for f in files if f.endswith(".h")]
    deps = []
    for f in header_files:
        src_pkg = config.infer_package(f)
        for dep in extract_project_includes(f, header_files):
            for hf in header_files:
                if os.path.basename(hf) == dep:
                    dst_pkg = config.infer_package(hf)
                    if src_pkg and dst_pkg:
                        deps.append((src_pkg, dst_pkg))
                    break
    return deps


def _build_cmake_deps(input_path):
    base = input_path if os.path.isdir(input_path) else os.path.dirname(input_path)
    targets, cmake_deps = extract_cmake_deps(base)
    if not targets:
        return None
    deps = []
    for target, libs in cmake_deps.items():
        for lib in libs:
            if lib in targets:
                deps.append((target, lib))
    return deps


def _transitive_reduction(deps):
    edges = set()
    for src, dst in deps:
        if src and dst and src != dst:
            edges.add((src, dst))

    adj = {}
    for src, dst in edges:
        adj.setdefault(src, set()).add(dst)

    def reachable_without_direct(start, skip_target):
        visited = set()
        stack = [n for n in adj.get(start, set()) if n != skip_target]
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            stack.extend(adj.get(node, set()) - visited)
        return visited

    reduced = []
    for src, dst in edges:
        if dst not in reachable_without_direct(src, dst):
            reduced.append((src, dst))
    return reduced


def _run_plantuml(puml_path, fmt, plantuml_bin):
    if fmt == "svg":
        subprocess.run([plantuml_bin, "-tsvg", puml_path], check=True)
    else:
        subprocess.run([plantuml_bin, puml_path], check=True)


def _get_plantuml_bin(args):
    if not (args.png or args.svg):
        return None
    plantuml_bin = shutil.which("plantuml")
    if not plantuml_bin:
        logger.error("plantuml not found in PATH. Install it: sudo apt install plantuml")
        sys.exit(1)
    return plantuml_bin


def _write_and_render(puml, output_path, plantuml_bin, args):
    with open(output_path, "w") as out:
        out.write(puml)
    logger.info("Written %s", output_path)
    if plantuml_bin:
        if args.svg:
            _run_plantuml(output_path, "svg", plantuml_bin)
            logger.info("SVG generated")
        if args.png:
            _run_plantuml(output_path, "png", plantuml_bin)
            logger.info("PNG generated")


def _associate_macros(macros, structs, config):
    from domain.models import FunctionModel, StructModel
    struct_names = sorted(structs.keys(), key=len, reverse=True)
    for macro in macros:
        target = None
        name_lower = macro.name.lower()
        for sname in struct_names:
            if sname.lower().replace("_t", "") in name_lower:
                target = sname
                break
        if target is None:
            parts = macro.name.split("_")
            if len(parts) >= 2:
                candidate = "_".join(parts[:2]) + "_t"
                if candidate in structs:
                    target = candidate
                elif not candidate.startswith("__"):
                    structs[candidate] = StructModel(name=candidate, file=macro.file)
                    target = candidate
        if target is None:
            continue
        if macro.is_function:
            params = [("param", p) for p in macro.parameters if p != "..."]
            f = FunctionModel(name=macro.name, parameters=params, return_type="macro", file=macro.file)
            if not any(m.name == macro.name for m in structs[target].methods):
                structs[target].methods.append(f)
        else:
            attr = ("const", macro.name)
            if attr not in structs[target].attributes:
                structs[target].attributes.append(attr)


def _build_usage_relations(files, structs, config):
    from domain.models import RelationModel
    func_to_struct = {}
    for s in structs.values():
        for m in s.methods:
            func_to_struct[m.name] = s.name

    relations = []
    seen = set()
    c_files = [f for f in files if f.endswith(".c") and not config.is_excluded(f)]
    for f in c_files:
        src_pkg = config.infer_package(f)
        calls = extract_function_calls(f)
        caller_structs = set()
        called_structs = set()
        for call in calls:
            if call in func_to_struct:
                called_structs.add(func_to_struct[call])
            for sname in structs:
                base = sname.lower().replace("_t", "")
                if base and call.lower().startswith(base + "_"):
                    caller_structs.add(sname)
                    break

        file_struct = None
        for sname in structs:
            base = sname.lower().replace("_t", "")
            if base and base in os.path.basename(f).lower():
                file_struct = sname
                break

        source = file_struct
        if source:
            for target in called_structs:
                if target != source:
                    key = (source, target, "usage")
                    if key not in seen:
                        seen.add(key)
                        relations.append(RelationModel(source=source, target=target, type="usage"))

    return relations



_INIT_TEMPLATE = """# =============================================================================
# Configuração do c2uml
# =============================================================================
# Coloque este arquivo na raiz do diretório a ser analisado.
# Todas as opções são opcionais — o c2uml usa defaults sensatos sem este arquivo.
# Descomente e ajuste conforme a estrutura do seu projeto.

# =============================================================================
# Diretórios de include extras
# =============================================================================
# Adiciona diretórios ao pré-processador C (-I). Útil quando o projeto tem
# headers em locais não convencionais ou dependências externas.
#
# include_dirs:
#   - vendor/include
#   - third_party/cJSON
#   - /usr/local/include

# =============================================================================
# Regras de agrupamento em pacotes
# =============================================================================
# O c2uml agrupa arquivos em pacotes (módulos) para o diagrama.
# Existem 3 mecanismos, aplicados nesta ordem:
#
# 1. rules   → regras explícitas por glob pattern (maior prioridade)
# 2. markers → infere pelo nome do diretório pai de um marker
# 3. groups  → agrupa pacotes em hierarquias (ex: builtin/optionals)
#
# packages:
#
#   # --- Markers ---
#   # Nomes de diretório que indicam "o diretório acima de mim é um pacote".
#   # Exemplo: em modulo/lib/src/foo.c, se "lib" é marker, o pacote é "modulo".
#   #
#   # Default: [lib, include, src, public, private]
#   #
#   # Estrutura típica (sat):
#   #   modules/builtin/sat_cache/lib/src/sat_cache.c  → pacote: sat_cache
#   #   modules/builtin/sat_cache/lib/include/sat_cache.h  → pacote: sat_cache
#   #
#   # Estrutura com components:
#   #   components/wifi/src/wifi.c  → pacote: wifi (se "src" é marker)
#   #
#   markers:
#     - lib
#     - include
#     - src
#
#   # --- Groups ---
#   # Nomes de diretório que agrupam pacotes numa hierarquia visual.
#   # No diagrama, pacotes dentro de "builtin/" ficam agrupados.
#   #
#   # Default: [builtin, optionals, modules, drivers, core, plugins]
#   #
#   groups:
#     - builtin
#     - optionals
#     - drivers
#     - core
#     - plugins
#     - hal
#
#   # --- Rules ---
#   # Regras explícitas: arquivos que casam com o pattern pertencem ao pacote.
#   # Têm prioridade sobre markers. Útil para casos especiais.
#   #
#   # Exemplos:
#   rules:
#     # Tudo em modules/main/ vira o pacote "core"
#     - pattern: "*/modules/main/*"
#       name: "core"
#
#     # Todos os drivers num único pacote
#     - pattern: "*/drivers/*"
#       name: "drivers"
#
#     # Projeto flat: agrupar por prefixo do arquivo
#     - pattern: "*/src/http_*"
#       name: "http"
#     - pattern: "*/src/db_*"
#       name: "database"
#     - pattern: "*/src/auth_*"
#       name: "auth"

# =============================================================================
# Visibilidade
# =============================================================================
# Define quais paths geram visibilidade pública (+) ou privada (-) no diagrama.
# Headers em paths "public" geram +, em paths "private" geram -.
# Funções static e funções definidas só no .c sempre geram - (privado).
#
# visibility:
#   public:
#     - "include/public/"
#     - "include/api/"
#     - "include/"           # tudo em include/ é público
#   private:
#     - "include/private/"
#     - "src/internal/"

# =============================================================================
# Exclusões
# =============================================================================
# Arquivos e diretórios a ignorar (glob patterns).
# Estes são SOMADOS aos defaults: */samples/*, */tests/*, */test/*, */examples/*
#
# Aceita:
#   - Nome de arquivo: "test_*.c" (casa com o basename)
#   - Path com diretório: "*/vendor/*" (casa com qualquer arquivo dentro de vendor/)
#
# exclude:
#   - "test_*"
#   - "*_test.c"
#   - "*_mock.c"
#   - "*_sample.c"
#   - "*/vendor/*"
#   - "*/third_party/*"
#   - "*/build/*"
#   - "*/deprecated/*"

# =============================================================================
# Exemplos de configuração por tipo de projeto
# =============================================================================
#
# --- Projeto com CMake (ex: sat) ---
# O c2uml detecta CMakeLists.txt automaticamente e usa target_link_libraries
# como fonte de dependências. Basta rodar:
#   python -m cli.main meu_projeto --mode module -o output/ --svg
#
# --- Projeto flat (tudo em src/) ---
# Use rules para agrupar por prefixo:
#   packages:
#     rules:
#       - pattern: "*/src/net_*"
#         name: "network"
#       - pattern: "*/src/ui_*"
#         name: "ui"
#       - pattern: "*/src/db_*"
#         name: "database"
#
# --- Projeto embedded (com HAL/BSP/App) ---
#   packages:
#     markers:
#       - src
#       - inc
#     groups:
#       - hal
#       - bsp
#       - app
#       - middleware
#
# --- Monorepo com vários componentes ---
#   packages:
#     markers:
#       - src
#       - include
#     rules:
#       - pattern: "*/libs/*"
#         name: "libs"
#   exclude:
#     - "*/tools/*"
#     - "*/scripts/*"
"""


def _generate_init():
    path = os.path.join(os.getcwd(), ".c2uml.yaml")
    if os.path.exists(path):
        logger.error(".c2uml.yaml already exists in current directory")
        sys.exit(1)
    with open(path, "w") as f:
        f.write(_INIT_TEMPLATE)
    logger.info("Created %s", path)


def main():
    parser = argparse.ArgumentParser(description="Generate PlantUML class diagrams from C code")
    parser.add_argument("input", nargs="?", help="C file or directory to analyze")
    parser.add_argument("-o", "--output", default=None, help="Output .puml file or directory")
    parser.add_argument("--mode", choices=["full", "structs", "module", "deps"], default="full",
                        help="full | structs | module | deps")
    parser.add_argument("--filter", help="Show only this package and its dependencies")
    parser.add_argument("--png", action="store_true", help="Generate PNG via plantuml")
    parser.add_argument("--svg", action="store_true", help="Generate SVG via plantuml")
    parser.add_argument("--quiet", action="store_true", help="Suppress warnings, show summary only")
    parser.add_argument("--all-deps", action="store_true", help="Show all dependencies (including transitive)")
    parser.add_argument("--init", action="store_true", help="Generate a .c2uml.yaml template in current directory")
    args = parser.parse_args()

    if args.init:
        _generate_init()
        return

    if not args.input:
        parser.error("the following arguments are required: input")

    if args.output is None:
        base = os.path.basename(os.path.abspath(args.input).rstrip(os.sep))
        if base.endswith((".c", ".h")):
            base = os.path.splitext(base)[0]
        args.output = f"{base}.puml"

    config = load_config(args.input)

    files = load_files(args.input)
    if not files:
        logger.error("No .c or .h files found in '%s'", args.input)
        sys.exit(1)

    files.sort(key=lambda f: (0 if f.endswith('.h') else 1, f))

    extra_dirs = [os.path.abspath(d) for d in config.include_dirs if os.path.isdir(d)]
    include_dirs = collect_include_dirs(os.path.abspath(args.input)) + extra_dirs

    all_structs, all_relations, all_enums, all_callbacks = _build_models(
        files, include_dirs, config, quiet=args.quiet)
    include_deps = _build_include_deps(files, config)
    cmake_deps = _build_cmake_deps(args.input)

    if cmake_deps is not None and not args.all_deps:
        include_deps = cmake_deps
    elif not args.all_deps:
        include_deps = _transitive_reduction(include_deps)

    all_macros = []
    for f in files:
        if f.endswith(".h") and not config.is_excluded(f):
            all_macros.extend(extract_macros(f))

    _associate_macros(all_macros, all_structs, config)

    # Feature 5: usage relations from function calls in .c files
    usage_relations = _build_usage_relations(files, all_structs, config)
    all_relations.extend(usage_relations)

    gen = PlantUMLGenerator(config)
    plantuml_bin = _get_plantuml_bin(args)

    if args.mode == "structs":
        all_relations = []
        include_deps = []

    if args.mode == "deps":
        packages = gen._group_by_package(all_structs, all_enums, all_callbacks)
        puml = gen.generate_deps(include_deps, packages)
        _write_and_render(puml, args.output, plantuml_bin, args)

    elif args.mode == "module":
        out_dir = args.output if not args.output.endswith(".puml") else "modules_out"
        os.makedirs(out_dir, exist_ok=True)

        packages = gen._group_by_package(all_structs, all_enums, all_callbacks)
        module_names = []
        for pkg_name in sorted(packages):
            if pkg_name == "default":
                continue
            puml = gen.generate_module(pkg_name, packages, all_relations, include_deps)
            if puml:
                path = os.path.join(out_dir, f"{pkg_name}.puml")
                with open(path, "w") as out:
                    out.write(puml)
                module_names.append(pkg_name)
                if plantuml_bin:
                    if args.svg:
                        _run_plantuml(path, "svg", plantuml_bin)
                        # Generate collapsed version
                        puml_c = gen.generate_module_collapsed(pkg_name, packages, all_relations, include_deps)
                        if puml_c:
                            cpath = os.path.join(out_dir, f"{pkg_name}.collapsed.puml")
                            with open(cpath, "w") as out:
                                out.write(puml_c)
                            _run_plantuml(cpath, "svg", plantuml_bin)
                    if args.png:
                        _run_plantuml(path, "png", plantuml_bin)

        if (args.svg or args.png) and module_names:
            if args.svg:
                for pkg_name in module_names:
                    svg_path = os.path.join(out_dir, f"{pkg_name}.svg")
                    viewer = generate_viewer_html(
                        pkg_name, svg_path, module_names, packages, include_deps)
                    if viewer:
                        vpath = os.path.join(out_dir, f"{pkg_name}.html")
                        with open(vpath, "w") as vf:
                            vf.write(viewer)

            idx = generate_index_html(out_dir, module_names, args.svg, args.png,
                                       packages, include_deps)
            logger.info("Written index: %s", idx)

        logger.info("Written %d module diagrams to %s/", len(module_names), out_dir)

    elif args.filter:
        packages = gen._group_by_package(all_structs, all_enums, all_callbacks)
        if args.filter not in packages:
            logger.error("Package '%s' not found. Available: %s",
                         args.filter, ", ".join(sorted(p for p in packages if p != "default")))
            sys.exit(1)
        puml = gen.generate_module(args.filter, packages, all_relations, include_deps)
        _write_and_render(puml, args.output, plantuml_bin, args)

    else:
        puml = gen.generate(all_structs, all_relations, all_enums, all_callbacks,
                            include_deps)
        _write_and_render(puml, args.output, plantuml_bin, args)


if __name__ == "__main__":
    main()
