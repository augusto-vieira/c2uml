import os

from config.loader import Config


class PlantUMLGenerator:

    RELATION_ARROWS = {
        "composition": "*--",
        "association": "-->",
        "dependency": "..>",
        "inheritance": "--|>",
        "usage": "..>",
    }

    SKIN = [
        "skinparam class {",
        "  BackgroundColor #FEF3C7",
        "  BorderColor #2980B9",
        "  ArrowColor #2C3E50",
        "  FontName Monospaced",
        "  FontSize 13",
        "  FontStyle bold",
        "  AttributeFontSize 11",
        "  AttributeFontName Monospaced",
        "  StereotypeFontSize 10",
        "  StereotypeFontStyle bold",
        "}",

        "skinparam interface {",
        "  BackgroundColor #E8DAEF",
        "  BorderColor #8E44AD",
        "  FontName Monospaced",
        "  FontSize 13",
        "  FontStyle bold",
        "  StereotypeFontStyle bold",
        "}",
        "skinparam enum {",
        "  BackgroundColor #FADBD8",
        "  BorderColor #27AE60",
        "  FontName Monospaced",
        "  FontSize 13",
        "  FontStyle bold",
        "  StereotypeFontStyle bold",
        "}",
        "skinparam package {",
        "  BackgroundColor #FDFEFE",
        "  BorderColor #5DADE2",
        "  FontSize 14",
        "  FontStyle bold",
        "}",
        "skinparam ArrowFontSize 10",
        "skinparam ArrowFontName Monospaced",
        "skinparam defaultFontSize 11",
        "skinparam defaultFontName Monospaced",
        "skinparam nodesep 60",
        "skinparam ranksep 40",
        "skinparam padding 3",
        "skinparam groupInheritance 2",
        "skinparam linetype ortho",
        "",
    ]

    SKIN_DEPS = [
        "left to right direction",
        "skinparam package {",
        "  BackgroundColor #FDFEFE",
        "  BorderColor #5DADE2",
        "  FontSize 14",
        "  FontStyle bold",
        "  FontName Monospaced",
        "}",
        "skinparam ArrowColor #2C3E50",
        "skinparam nodesep 30",
        "skinparam ranksep 50",
        "",
    ]

    LEGEND = [
        "",
        "legend right",
        "  <b><font:Monospaced>c2uml</font></b> — C to UML class diagram",
        "  |= Color |= Element |",
        "  | <back:#FEF3C7>  class  </back> | struct / typedef |",
        "  | <back:#EBF5FB>  class  </back> | opaque pointer |",
        "  | <back:#D5F5E3>  class  </back> | union |",
        "  | <back:#FADBD8>  enum  </back> | enumeration |",
        "  | <back:#E8DAEF>  iface  </back> | callback (fn ptr) |",
        "  |= Icon |= Visibility |",
        "  | <color:#1A8F3C>●</color> circle green | + public attribute (.h) |",
        "  | <color:#1A8F3C>○</color> circle green | + public method (.h) |",
        "  | <color:#C0392B>■</color> square red | - private attribute (.c) |",
        "  | <color:#C0392B>□</color> square red | - private method (static/.c) |",
        "  |= Arrow |= Relation |",
        "  | *-- | composition |",
        "  | --> | association (pointer) |",
        "  | --|> | inheritance (1st field) |",
        "  | ..> | dependency / usage |",
        "  |= Style |= Meaning |",
        "  | <color:#1A8F3C>green text</color> | <<create>> constructor |",
        "  | <color:#C0392B>red text</color> | <<destroy>> destructor |",
        "  | <color:#2471A3>blue text</color> | macro function |",
        "  | <color:#7F8C8D><i>gray italic</i></color> | #define constant |",
        "endlegend",
    ]

    def __init__(self, config=None):
        self.config = config or Config()

    @staticmethod
    def _method_stereotype(name):
        lower = name.lower()
        for suffix in ("_create", "_new", "_init", "_open"):
            if lower.endswith(suffix) or suffix + "_" in lower:
                return "<<create>>"
        for suffix in ("_destroy", "_free", "_close", "_release"):
            if lower.endswith(suffix):
                return "<<destroy>>"
        return ""

    def _format_method(self, m, visibility="+"):
        parts = []
        for t, n in m.parameters:
            if t == "..." or n == "...":
                continue
            elif n is None:
                parts.append(str(t))
            else:
                parts.append(f"{n}: {t}")
        params = ", ".join(parts)
        stereo = self._method_stereotype(m.name)
        vis_color = "#777" if visibility == "-" else "#000"
        if m.return_type == "macro":
            return f"    {visibility} <color:#2471A3>{m.name}({params}): macro</color>"
        if stereo == "<<create>>":
            return f"    {visibility} <color:#1A8F3C>{m.name}({params}): {m.return_type} {stereo}</color>"
        if stereo == "<<destroy>>":
            return f"    {visibility} <color:#C0392B>{m.name}({params}): {m.return_type} {stereo}</color>"
        return f"    {visibility} <color:{vis_color}>{m.name}({params}): {m.return_type}</color>"

    def _method_visibility(self, m, struct_vis):
        if m.is_static:
            return "-"
        if m.file.endswith(".c"):
            return "-"
        return struct_vis

    STEREO_COLORS = {
        "opaque": "#EBF5FB",
        "union": "#D5F5E3",
    }

    def _format_struct(self, s):
        vis = self.config.infer_visibility(s.file)
        stereo = f" <<{s.stereotype}>>" if s.stereotype else ""
        color = self.STEREO_COLORS.get(s.stereotype, "")
        color_str = f" {color}" if color else ""
        lines = [f"  class {s.name}{stereo}{color_str} {{"]
        for t, n in s.attributes:
            if t == "const":
                lines.append(f"    {vis} <color:#7F8C8D><i>{n} : const</i></color>")
            else:
                lines.append(f"    {vis} {n} : {t}")
        for m in s.methods:
            mvis = self._method_visibility(m, vis)
            lines.append(self._format_method(m, mvis))
        lines.append("  }")
        return lines

    def _format_enum(self, e):
        lines = [f"  enum {e.name} <<enumeration>> #FADBD8 {{"]
        for v in e.values:
            lines.append(f"    {v}")
        lines.append("  }")
        return lines

    def _format_callback(self, cb):
        vis = self.config.infer_visibility(cb.file)
        params = ", ".join(f"{n}: {t}" for t, n in cb.parameters)
        lines = [
            f"  interface {cb.name} <<callback>> #E8DAEF {{",
            f"    {vis} invoke({params}): {cb.return_type}",
            "  }",
        ]
        return lines

    def _group_by_package(self, structs, enums, callbacks):
        packages = {}
        for s in structs.values():
            pkg = self.config.infer_package(s.file) or "default"
            grp = self.config.infer_group(s.file)
            packages.setdefault(pkg, {"structs": [], "enums": [], "callbacks": [], "group": grp})
            packages[pkg]["structs"].append(s)
        for e in enums.values():
            pkg = self.config.infer_package(e.file) or "default"
            grp = self.config.infer_group(e.file)
            packages.setdefault(pkg, {"structs": [], "enums": [], "callbacks": [], "group": grp})
            packages[pkg]["enums"].append(e)
        for cb in callbacks.values():
            pkg = self.config.infer_package(cb.file) or "default"
            grp = self.config.infer_group(cb.file)
            packages.setdefault(pkg, {"structs": [], "enums": [], "callbacks": [], "group": grp})
            packages[pkg]["callbacks"].append(cb)
        return packages

    def _is_valid_package(self, pkg):
        for s in pkg["structs"] + pkg["callbacks"]:
            norm = os.path.normpath(s.file)
            if os.sep + "lib" + os.sep in norm or os.sep + "include" + os.sep in norm:
                return True
        for e in pkg["enums"]:
            norm = os.path.normpath(e.file)
            if os.sep + "lib" + os.sep in norm or os.sep + "include" + os.sep in norm:
                return True
        return not pkg["structs"] and not pkg["enums"] and not pkg["callbacks"]

    def _render_package_contents(self, pkg):
        lines = []
        for s in pkg["structs"]:
            lines.extend(self._format_struct(s))
        for e in pkg["enums"]:
            lines.extend(self._format_enum(e))
        for cb in pkg["callbacks"]:
            lines.extend(self._format_callback(cb))
        return lines

    def generate(self, structs, relations, enums=None, callbacks=None,
                 include_deps=None):
        enums = enums or {}
        callbacks = callbacks or {}
        include_deps = include_deps or []

        packages = self._group_by_package(structs, enums, callbacks)

        groups = {}
        for pkg_name, pkg in packages.items():
            if pkg_name != "default" and not self._is_valid_package(pkg):
                continue
            grp = pkg.get("group") or "default"
            groups.setdefault(grp, {})
            groups[grp][pkg_name] = pkg

        lines = ["@startuml"]
        lines.extend(self.SKIN)

        for grp_name in sorted(groups):
            grp_pkgs = groups[grp_name]
            if grp_name == "default":
                for pkg_name in sorted(grp_pkgs):
                    pkg = grp_pkgs[pkg_name]
                    if pkg_name == "default":
                        lines.extend(self._render_package_contents(pkg))
                    else:
                        lines.append(f'package "{pkg_name}" {{')
                        lines.extend(self._render_package_contents(pkg))
                        lines.append("}")
            else:
                lines.append(f'package "{grp_name}" {{')
                for pkg_name in sorted(grp_pkgs):
                    pkg = grp_pkgs[pkg_name]
                    if pkg_name == "default" or pkg_name == grp_name:
                        lines.extend(self._render_package_contents(pkg))
                    else:
                        lines.append(f'  package "{pkg_name}" {{')
                        lines.extend(self._render_package_contents(pkg))
                        lines.append("  }")
                lines.append("}")

        for r in relations:
            arrow = self.RELATION_ARROWS.get(r.type, "-->")
            lines.append(f"{r.source} {arrow} {r.target}")

        seen_deps = set()
        for src_pkg, dst_pkg in include_deps:
            if src_pkg and dst_pkg and src_pkg != dst_pkg:
                key = (src_pkg, dst_pkg)
                if key not in seen_deps:
                    seen_deps.add(key)
                    lines.append(f'"{src_pkg}" ..> "{dst_pkg}"')

        lines.extend(self.LEGEND)
        lines.append("@enduml")
        return "\n".join(lines)

    def _module_lines(self, pkg_name, packages, all_relations, include_deps, collapsed=False):
        pkg = packages[pkg_name]
        local_names = set()
        for s in pkg["structs"]:
            local_names.add(s.name)
        for e in pkg["enums"]:
            local_names.add(e.name)
        for cb in pkg["callbacks"]:
            local_names.add(cb.name)

        dep_packages = set()
        for src, dst in include_deps:
            if src == pkg_name and dst != pkg_name:
                dep_packages.add(dst)

        lines = ["@startuml"]
        if collapsed:
            lines.append("hide members")
        lines.extend(self.SKIN)
        lines.append(f'package "{pkg_name}" {{')
        lines.extend(self._render_package_contents(pkg))
        lines.append("}")

        for r in all_relations:
            if r.source in local_names and r.target in local_names:
                arrow = self.RELATION_ARROWS.get(r.type, "-->")
                lines.append(f"{r.source} {arrow} {r.target}")

        for dep in sorted(dep_packages):
            lines.append(f'package "{dep}" {{')
            lines.append("}")

        for dep in sorted(dep_packages):
            lines.append(f'"{pkg_name}" ..> "{dep}"')

        lines.append("@enduml")
        return "\n".join(lines)

    def generate_module(self, pkg_name, packages, all_relations, include_deps):
        if pkg_name not in packages:
            return None
        return self._module_lines(pkg_name, packages, all_relations, include_deps)

    def generate_module_collapsed(self, pkg_name, packages, all_relations, include_deps):
        if pkg_name not in packages:
            return None
        return self._module_lines(pkg_name, packages, all_relations, include_deps, collapsed=True)

    def generate_deps(self, include_deps, packages=None):
        lines = ["@startuml"]
        lines.extend(self.SKIN_DEPS)
        all_pkgs = set()
        seen = set()
        for src, dst in include_deps:
            if src and dst and src != dst:
                all_pkgs.add(src)
                all_pkgs.add(dst)
                key = (src, dst)
                if key not in seen:
                    seen.add(key)

        if packages:
            groups = {}
            for pkg_name in all_pkgs:
                grp = packages[pkg_name].get("group") if pkg_name in packages else None
                grp = grp or "default"
                groups.setdefault(grp, set())
                groups[grp].add(pkg_name)

            for grp_name in sorted(groups):
                if grp_name == "default":
                    for pkg in sorted(groups[grp_name]):
                        lines.append(f'package "{pkg}"')
                else:
                    non_self = [p for p in sorted(groups[grp_name]) if p != grp_name]
                    if non_self:
                        lines.append(f'package "{grp_name}" {{')
                        for pkg in non_self:
                            lines.append(f'  package "{pkg}"')
                        lines.append("}")
                    else:
                        lines.append(f'package "{grp_name}"')
        else:
            for pkg in sorted(all_pkgs):
                lines.append(f'package "{pkg}"')

        for src, dst in sorted(seen):
            lines.append(f'"{src}" ..> "{dst}"')

        lines.append("@enduml")
        return "\n".join(lines)
