"""
Testes de integração do c2uml.

Testa o fluxo completo: parsing → modelo → geração PlantUML.
"""
import os
import tempfile
import pytest

from domain.models import StructModel, FunctionModel, RelationModel
from analyzer.model_builder import ModelBuilder
from generator.plantuml_generator import PlantUMLGenerator
from utils.file_loader import load_files
from parser.c_parser import parse_c_file


SAMPLE_C = """\
typedef struct {
    int id;
    char name[50];
} Pessoa;

typedef struct {
    Pessoa* pessoa;
    float valor;
} Conta;

void Pessoa_init(Pessoa* p, int id);
float Conta_saldo(Conta* c);
"""


def _write_temp_c(content, suffix=".h"):
    f = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False)
    f.write(content)
    f.close()
    return f.name


class TestModelos:
    """Dataclasses do domínio têm defaults sensatos."""

    def test_struct_tem_listas_vazias_por_padrao(self):
        """StructModel sem argumentos tem attributes e methods vazios."""
        s = StructModel(name="Foo")
        assert s.attributes == []
        assert s.methods == []

    def test_funcao_tem_void_e_params_vazios_por_padrao(self):
        """FunctionModel sem argumentos tem return_type='void' e parameters vazios."""
        f = FunctionModel(name="bar")
        assert f.return_type == "void"
        assert f.parameters == []

    def test_relacao_armazena_source_e_target(self):
        """RelationModel guarda source, target e type."""
        r = RelationModel(source="A", target="B", type="association")
        assert r.source == "A"


class TestModelBuilder:
    """O ModelBuilder extrai structs, relações e métodos da AST do pycparser."""

    @pytest.fixture(autouse=True)
    def setup(self):
        path = _write_temp_c(SAMPLE_C)
        self.path = path
        ast = parse_c_file(path)
        self.builder = ModelBuilder(path)
        self.builder.visit(ast)
        self.structs, self.relations, self.enums, self.callbacks = self.builder.finalize()
        yield
        os.unlink(path)

    def test_encontra_structs(self):
        """Extrai Pessoa e Conta do código C."""
        assert "Pessoa" in self.structs
        assert "Conta" in self.structs

    def test_extrai_atributos(self):
        """Pessoa tem atributos int e char[]."""
        attrs = self.structs["Pessoa"].attributes
        types = [t for t, _ in attrs]
        assert "int" in types
        assert "char[]" in types

    def test_associa_metodo_pelo_primeiro_parametro_ponteiro(self):
        """Pessoa_init(Pessoa* p, ...) é associado à struct Pessoa."""
        methods = [m.name for m in self.structs["Pessoa"].methods]
        assert "Pessoa_init" in methods

    def test_associa_metodo_a_conta(self):
        """Conta_saldo(Conta* c) é associado à struct Conta."""
        methods = [m.name for m in self.structs["Conta"].methods]
        assert "Conta_saldo" in methods

    def test_nao_duplica_metodos(self):
        """Cada método aparece uma única vez na struct."""
        for s in self.structs.values():
            names = [m.name for m in s.methods]
            assert len(names) == len(set(names))

    def test_relacao_conta_para_pessoa_por_ponteiro(self):
        """Conta tem Pessoa* → gera relação de associação."""
        rel = [r for r in self.relations if r.source == "Conta" and r.target == "Pessoa"]
        assert len(rel) == 1
        assert rel[0].type == "association"

    def test_extrai_tipo_de_retorno(self):
        """Conta_saldo retorna float."""
        conta_methods = {m.name: m for m in self.structs["Conta"].methods}
        assert conta_methods["Conta_saldo"].return_type == "float"


class TestGeradorPlantUML:
    """O PlantUMLGenerator produz .puml válido a partir dos modelos."""

    def test_gera_classe_com_atributos(self):
        """Struct com atributo gera 'class Foo { x : int }'."""
        structs = {"Foo": StructModel(name="Foo", attributes=[("int", "x")])}
        gen = PlantUMLGenerator()
        result = gen.generate(structs, [])
        assert "class Foo {" in result
        assert "x : int" in result

    def test_gera_relacoes(self):
        """Relação de composição gera 'A *-- B'."""
        structs = {
            "A": StructModel(name="A"),
            "B": StructModel(name="B"),
        }
        rels = [RelationModel(source="A", target="B", type="composition")]
        gen = PlantUMLGenerator()
        result = gen.generate(structs, rels)
        assert "A *-- B" in result

    def test_gera_metodo_com_parametros(self):
        """Método com parâmetros gera 'do_thing(x: int): void'."""
        f = FunctionModel(name="do_thing", parameters=[("int", "x")], return_type="void")
        structs = {"S": StructModel(name="S", methods=[f])}
        gen = PlantUMLGenerator()
        result = gen.generate(structs, [])
        assert "do_thing(x: int): void" in result


class TestCarregadorArquivos:
    """O file_loader carrega arquivos .c e .h, ignorando outros."""

    def test_carrega_arquivo_unico(self):
        """Aceita um arquivo .c como entrada."""
        path = _write_temp_c("int x;", suffix=".c")
        assert load_files(path) == [path]
        os.unlink(path)

    def test_ignora_arquivos_nao_c(self):
        """Arquivo .txt não é carregado."""
        path = tempfile.NamedTemporaryFile(suffix=".txt", delete=False).name
        assert load_files(path) == []
        os.unlink(path)

    def test_carrega_diretorio_com_c_e_h(self, tmp_path):
        """Diretório com .c, .h e .txt carrega apenas .c e .h."""
        (tmp_path / "a.c").write_text("int a;")
        (tmp_path / "b.h").write_text("int b;")
        (tmp_path / "c.txt").write_text("nope")
        files = load_files(str(tmp_path))
        assert len(files) == 2
        assert all(f.endswith((".c", ".h")) for f in files)
