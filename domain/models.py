from dataclasses import dataclass, field

@dataclass
class FunctionModel:
    name: str
    parameters: list = field(default_factory=list)
    return_type: str = "void"
    file: str = ""
    is_static: bool = False

@dataclass
class StructModel:
    name: str
    attributes: list = field(default_factory=list)
    methods: list = field(default_factory=list)
    file: str = ""
    stereotype: str = ""

@dataclass
class RelationModel:
    source: str
    target: str
    type: str  # "association", "composition", "dependency"

@dataclass
class EnumModel:
    name: str
    values: list = field(default_factory=list)
    file: str = ""

@dataclass
class CallbackModel:
    name: str
    parameters: list = field(default_factory=list)
    return_type: str = "void"
    file: str = ""

@dataclass
class MacroModel:
    name: str
    parameters: list = field(default_factory=list)
    is_function: bool = False
    value: str = ""
    file: str = ""
