import logging

from pycparser import c_ast
from domain.models import StructModel, FunctionModel, RelationModel, EnumModel, CallbackModel

logger = logging.getLogger(__name__)


_SYSTEM_STRUCTS = {"sockaddr", "addrinfo", "timeval", "timespec", "tm",
                   "stat", "dirent", "iovec", "msghdr", "cmsghdr",
                   "pollfd", "epoll_event", "sigaction", "itimerval"}


class ModelBuilder(c_ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.structs = {}
        self.enums = {}
        self.callbacks = {}
        self.functions = []
        self.relations = []

    def _type_to_str(self, t):
        if isinstance(t, c_ast.TypeDecl):
            if isinstance(t.type, c_ast.IdentifierType):
                return " ".join(t.type.names)
            if isinstance(t.type, c_ast.Struct):
                return t.type.name or "anon"
            if isinstance(t.type, c_ast.Union):
                return t.type.name or "anon"
        if isinstance(t, c_ast.PtrDecl):
            return self._type_to_str(t.type) + "*"
        if isinstance(t, c_ast.ArrayDecl):
            return self._type_to_str(t.type) + "[]"
        return "unknown"

    def _extract_return_type(self, func_decl):
        return self._type_to_str(func_decl.type)

    def _resolve_file(self, node):
        if node.coord and node.coord.file:
            return node.coord.file
        return self.filename

    def _add_struct(self, name, struct_node, coord=None):
        if not name or name in self.structs or name.startswith("__") or name in _SYSTEM_STRUCTS:
            return
        source_file = self._resolve_file(coord or struct_node) if (coord or struct_node.coord) else self.filename
        is_opaque = struct_node.decls is None
        stereo = "opaque" if is_opaque else ""
        s = StructModel(name=name, file=source_file, stereotype=stereo)
        if struct_node.decls:
            for d in struct_node.decls:
                t = self._type_to_str(d.type)
                if isinstance(d.type, c_ast.TypeDecl) and isinstance(d.type.type, c_ast.Struct):
                    nested = d.type.type
                    if nested.name and nested.decls:
                        self._add_struct(nested.name, nested)
                        s.attributes.append((nested.name, d.name))
                        continue
                s.attributes.append((t, d.name))
        self.structs[name] = s

    def _add_union(self, name, union_node, coord=None):
        if name and name not in self.structs and not name.startswith("__"):
            source_file = self._resolve_file(coord or union_node) if (coord or union_node.coord) else self.filename
            s = StructModel(name=name, file=source_file, stereotype="union")
            if union_node.decls:
                for d in union_node.decls:
                    t = self._type_to_str(d.type)
                    s.attributes.append((t, d.name))
            self.structs[name] = s

    def visit_Typedef(self, node):
        if isinstance(node.type.type, c_ast.Struct):
            self._add_struct(node.name, node.type.type, coord=node)
        elif isinstance(node.type.type, c_ast.Enum):
            self._add_enum(node.name, node.type.type, coord=node)
        elif isinstance(node.type.type, c_ast.Union):
            self._add_union(node.name, node.type.type, coord=node)
        elif isinstance(node.type, c_ast.PtrDecl) and isinstance(node.type.type, c_ast.FuncDecl):
            self._add_callback(node.name, node.type.type, coord=node)

    def visit_Decl(self, node):
        if isinstance(node.type, c_ast.FuncDecl):
            params = []
            if node.type.args:
                for p in node.type.args.params:
                    if isinstance(p, c_ast.EllipsisParam):
                        params.append(("...", None))
                    else:
                        t = self._type_to_str(p.type)
                        params.append((t, p.name))
            ret = self._extract_return_type(node.type)
            is_static = 'static' in (node.storage or [])
            source_file = self._resolve_file(node)
            f = FunctionModel(name=node.name, parameters=params, return_type=ret,
                              file=source_file, is_static=is_static)
            self.functions.append(f)
        elif isinstance(node.type, c_ast.Struct):
            self._add_struct(node.name or node.type.name, node.type, coord=node)
        elif isinstance(node.type, c_ast.Enum):
            self._add_enum(node.name or node.type.name, node.type, coord=node)
        elif isinstance(node.type, c_ast.Union):
            self._add_union(node.name or node.type.name, node.type, coord=node)

    def _add_enum(self, name, enum_node, coord=None):
        if name and name not in self.enums and not name.startswith("__"):
            source_file = self._resolve_file(coord or enum_node) if (coord or enum_node.coord) else self.filename
            values = []
            if enum_node.values:
                values = [e.name for e in enum_node.values.enumerators]
            self.enums[name] = EnumModel(name=name, values=values, file=source_file)

    def _add_callback(self, name, func_decl, coord=None):
        if name and name not in self.callbacks and not name.startswith("__"):
            source_file = self._resolve_file(coord or func_decl) if (coord or func_decl.coord) else self.filename
            params = []
            if func_decl.args:
                for p in func_decl.args.params:
                    if isinstance(p, c_ast.EllipsisParam):
                        params.append(("...", None))
                    else:
                        t = self._type_to_str(p.type)
                        params.append((t, getattr(p, 'name', None)))
            ret = self._type_to_str(func_decl.type)
            self.callbacks[name] = CallbackModel(
                name=name, parameters=params, return_type=ret, file=source_file
            )

    def _build_relations(self):
        struct_names = set(self.structs.keys())
        for s in self.structs.values():
            for idx, (attr_type, _) in enumerate(s.attributes):
                base = attr_type.replace("*", "").replace("[]", "").strip()
                if base in struct_names and base != s.name:
                    if idx == 0 and "*" not in attr_type and "[]" not in attr_type:
                        rel_type = "inheritance"
                    elif "*" in attr_type:
                        rel_type = "association"
                    else:
                        rel_type = "composition"
                    rel = RelationModel(source=s.name, target=base, type=rel_type)
                    if rel not in self.relations:
                        self.relations.append(rel)

    def _associate_methods(self):
        struct_names = set(self.structs.keys())
        for f in self.functions:
            assigned = False
            if f.parameters:
                first_type, _ = f.parameters[0]
                if first_type.endswith(("*", "[]")):
                    base = first_type.replace("*", "").replace("[]", "").strip()
                    if base in struct_names:
                        self.structs[base].methods.append(f)
                        assigned = True
            if not assigned:
                for sname in sorted(struct_names, key=len, reverse=True):
                    if sname.lower() in f.name.lower():
                        self.structs[sname].methods.append(f)
                        assigned = True
                        break
            if not assigned:
                self._create_struct_from_function(f)

    def _create_struct_from_function(self, func):
        parts = func.name.split("_")
        for i in range(len(parts) - 1, 0, -1):
            candidate = "_".join(parts[:i]) + "_t"
            if candidate not in self.structs:
                continue
            self.structs[candidate].methods.append(func)
            return
        if len(parts) >= 2:
            candidate = "_".join(parts[:2]) + "_t"
            if candidate.startswith("__"):
                return
            from domain.models import StructModel
            if candidate not in self.structs:
                self.structs[candidate] = StructModel(name=candidate, file=self.filename)
            self.structs[candidate].methods.append(func)

    def finalize(self):
        self._associate_methods()
        self._build_relations()
        return self.structs, self.relations, self.enums, self.callbacks
