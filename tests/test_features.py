"""
Testes das features do c2uml.

Cada teste documenta um comportamento esperado do sistema.
"""
import os
import tempfile

from config.loader import Config, load_config


class TestInferirPacote:
    """O c2uml infere o pacote de um arquivo pela estrutura de diretórios."""

    def test_marker_lib_identifica_pacote_pelo_diretorio_pai(self):
        """modulo/lib/src/foo.c → pacote 'modulo' (lib é marker)."""
        config = Config()
        assert config.infer_package("project/modules/sat_cache/lib/src/sat_cache.c") == "sat_cache"

    def test_marker_include_identifica_pacote_pelo_diretorio_pai(self):
        """modulo/include/foo.h → pacote 'modulo' (include é marker)."""
        config = Config()
        assert config.infer_package("project/modules/sat_cache/include/sat_cache.h") == "sat_cache"

    def test_marker_src_identifica_pacote_pelo_diretorio_pai(self):
        """componente/src/foo.c → pacote 'componente' (src é marker)."""
        config = Config()
        assert config.infer_package("project/components/wifi/src/wifi.c") == "wifi"

    def test_regra_explicita_tem_prioridade_sobre_markers(self):
        """Rules no yaml têm prioridade sobre inferência por markers."""
        config = Config({"packages": {"rules": [{"pattern": "*/modules/main/*", "name": "core"}]}})
        assert config.infer_package("project/modules/main/lib/src/main.c") == "core"

    def test_projeto_flat_usa_nome_do_diretorio_pai(self):
        """Sem markers, usa o diretório pai como pacote (fallback para projetos flat)."""
        config = Config()
        assert config.infer_package("examples/real_world/bank_account.h") == "real_world"

    def test_projeto_flat_com_um_nivel(self):
        """my_project/foo.c → pacote 'my_project'."""
        config = Config()
        assert config.infer_package("my_project/foo.c") == "my_project"

    def test_markers_customizados_no_yaml(self):
        """O yaml pode definir markers diferentes dos defaults."""
        config = Config({"packages": {"markers": ["inc", "source"]}})
        assert config.infer_package("project/driver/inc/driver.h") == "driver"

    def test_arquivo_na_raiz_nao_tem_pacote(self):
        """Arquivo solto na raiz (sem diretório pai) retorna None."""
        config = Config()
        assert config.infer_package("foo.c") is None


class TestExclusoes:
    """O c2uml exclui arquivos por glob patterns, com defaults sensatos."""

    def test_exclui_por_nome_de_arquivo(self):
        """Pattern 'test_*' casa com o basename do arquivo."""
        config = Config({"exclude": ["test_*"]})
        assert config.is_excluded("src/test_foo.c") is True

    def test_nao_exclui_arquivo_normal(self):
        """Arquivo que não casa com nenhum pattern não é excluído."""
        config = Config({"exclude": ["test_*"]})
        assert config.is_excluded("src/foo.c") is False

    def test_exclui_por_diretorio(self):
        """Pattern '*/vendor/*' exclui qualquer arquivo dentro de vendor/."""
        config = Config({"exclude": ["*/vendor/*"]})
        assert config.is_excluded("project/vendor/lib/foo.c") is True

    def test_nao_exclui_diretorio_diferente(self):
        """Pattern de diretório não casa com outros diretórios."""
        config = Config({"exclude": ["*/vendor/*"]})
        assert config.is_excluded("project/src/foo.c") is False

    def test_default_exclui_samples(self):
        """Diretório samples/ é excluído por padrão."""
        config = Config()
        assert config.is_excluded("project/modules/sat_opengl/samples/arc/src/main.c") is True

    def test_default_exclui_tests(self):
        """Diretório tests/ é excluído por padrão."""
        config = Config()
        assert config.is_excluded("project/modules/sat_cache/tests/test_cache.c") is True

    def test_default_exclui_examples(self):
        """Diretório examples/ é excluído por padrão."""
        config = Config()
        assert config.is_excluded("project/examples/demo.c") is True

    def test_default_nao_exclui_codigo_normal(self):
        """Código em lib/src/ não é excluído pelos defaults."""
        config = Config()
        assert config.is_excluded("project/modules/sat_cache/lib/src/sat_cache.c") is False

    def test_exclusoes_do_yaml_somam_com_defaults(self):
        """Exclusões do .c2uml.yaml são somadas aos defaults, não substituem."""
        config = Config({"exclude": ["*.bak"]})
        assert config.is_excluded("foo.bak") is True
        assert config.is_excluded("project/tests/test.c") is True


class TestCarregarConfig:
    """O c2uml carrega configuração do .c2uml.yaml ou usa defaults."""

    def test_carrega_yaml_do_diretorio(self):
        """Se existe .c2uml.yaml no diretório, carrega as configurações."""
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, ".c2uml.yaml"), "w") as f:
                f.write("exclude:\n  - '*.bak'\n")
            config = load_config(d)
            assert "*.bak" in config.exclude

    def test_usa_defaults_sem_yaml(self):
        """Sem .c2uml.yaml, usa os defaults sensatos."""
        with tempfile.TemporaryDirectory() as d:
            config = load_config(d)
            assert config.package_markers == ["lib", "include", "src", "public", "private"]


class TestReducaoTransitiva:
    """Dependências transitivas são removidas para limpar o diagrama.
    Se A→B e B→C, a dependência A→C é redundante e removida."""

    def test_remove_dependencia_transitiva(self):
        """A→B→C: remove A→C (alcançável via B)."""
        from cli.main import _transitive_reduction
        deps = [("A", "B"), ("B", "C"), ("A", "C")]
        reduced = _transitive_reduction(deps)
        assert ("A", "B") in reduced
        assert ("B", "C") in reduced
        assert ("A", "C") not in reduced

    def test_mantem_dependencias_diretas_independentes(self):
        """A→B e A→C sem caminho B→C: mantém ambas."""
        from cli.main import _transitive_reduction
        deps = [("A", "B"), ("A", "C")]
        reduced = _transitive_reduction(deps)
        assert ("A", "B") in reduced
        assert ("A", "C") in reduced

    def test_lista_vazia(self):
        """Sem dependências, retorna lista vazia."""
        from cli.main import _transitive_reduction
        assert _transitive_reduction([]) == []

    def test_ignora_self_loops(self):
        """Dependência de um pacote pra ele mesmo é ignorada."""
        from cli.main import _transitive_reduction
        deps = [("A", "A"), ("A", "B")]
        reduced = _transitive_reduction(deps)
        assert ("A", "B") in reduced
        assert ("A", "A") not in reduced


class TestDependenciasCMake:
    """O c2uml extrai dependências do CMakeLists.txt via target_link_libraries."""

    def test_extrai_targets_e_dependencias(self):
        """Parseia add_library e target_link_libraries corretamente."""
        from parser.c_parser import extract_cmake_deps
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "CMakeLists.txt"), "w") as f:
                f.write(
                    'add_library(foo "")\n'
                    'add_library(bar "")\n'
                    'add_library(baz "")\n'
                    'target_link_libraries(foo PUBLIC bar)\n'
                    'target_link_libraries(bar PUBLIC baz)\n'
                )
            targets, deps = extract_cmake_deps(d)
            assert "foo" in targets
            assert "bar" in targets
            assert "baz" in targets
            assert "bar" in deps["foo"]
            assert "baz" in deps["bar"]

    def test_reconhece_target_folha_sem_dependencias(self):
        """Target com add_library mas sem target_link_libraries é reconhecido.
        Corrige o bug onde sat_status sumia por ser folha."""
        from parser.c_parser import extract_cmake_deps
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "CMakeLists.txt"), "w") as f:
                f.write(
                    'add_library(leaf "")\n'
                    'add_library(parent "")\n'
                    'target_link_libraries(parent PUBLIC leaf)\n'
                )
            targets, deps = extract_cmake_deps(d)
            assert "leaf" in targets
            assert "leaf" in deps["parent"]

    def test_filtra_libs_do_sistema(self):
        """Libs do sistema (pthread, m) não são targets do projeto e são filtradas."""
        from cli.main import _build_cmake_deps
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "CMakeLists.txt"), "w") as f:
                f.write(
                    'add_library(mylib "")\n'
                    'target_link_libraries(mylib PUBLIC pthread m)\n'
                )
            result = _build_cmake_deps(d)
            assert result == []

    def test_retorna_none_sem_cmake(self):
        """Sem CMakeLists.txt, retorna None (fallback para #include)."""
        from cli.main import _build_cmake_deps
        with tempfile.TemporaryDirectory() as d:
            result = _build_cmake_deps(d)
            assert result is None


class TestResolucaoArquivoOriginal:
    """O ModelBuilder usa coord.file do pycparser para atribuir cada declaração
    ao arquivo onde foi realmente definida, não ao arquivo que fez #include."""

    def test_struct_incluida_pertence_ao_arquivo_original(self):
        """Quando connection.h inclui http_types.h, as structs do http_types.h
        devem ter file='http_types.h', não 'connection.h'.
        Corrige o bug onde o pacote http sumia no microservice."""
        from analyzer.model_builder import ModelBuilder
        from pycparser import CParser

        code = (
            '# 1 "http_types.h"\n'
            'typedef struct { int x; } http_t;\n'
            '# 1 "connection.h"\n'
            'typedef struct { int y; } connection_t;\n'
        )
        ast = CParser().parse(code, filename="connection.h")

        builder = ModelBuilder("connection.h")
        builder.visit(ast)
        structs, _, _, _ = builder.finalize()

        assert structs["http_t"].file == "http_types.h"
        assert structs["connection_t"].file == "connection.h"


class TestGeradorModulo:
    """O gerador de módulos produz .puml com o conteúdo correto."""

    def test_modulo_nao_tem_legenda(self):
        """A legenda foi movida para o viewer HTML, não aparece no .puml."""
        from generator.plantuml_generator import PlantUMLGenerator
        from domain.models import StructModel

        gen = PlantUMLGenerator()
        structs = {"foo_t": StructModel(name="foo_t", file="mod/lib/src/foo.c")}
        packages = gen._group_by_package(structs, {}, {})
        puml = gen.generate_module("mod", packages, [], [])
        assert "legend" not in puml.lower()

    def test_modulo_colapsado_tem_hide_members(self):
        """O .puml colapsado inclui 'hide members' para o PlantUML omitir atributos/métodos."""
        from generator.plantuml_generator import PlantUMLGenerator
        from domain.models import StructModel

        gen = PlantUMLGenerator()
        structs = {"foo_t": StructModel(name="foo_t", file="mod/lib/src/foo.c")}
        packages = gen._group_by_package(structs, {}, {})
        puml = gen.generate_module_collapsed("mod", packages, [], [])
        assert "hide members" in puml

    def test_modulo_mostra_pacotes_de_dependencia(self):
        """Dependências aparecem como pacotes declarados e setas ..> no .puml."""
        from generator.plantuml_generator import PlantUMLGenerator
        from domain.models import StructModel

        gen = PlantUMLGenerator()
        structs = {"foo_t": StructModel(name="foo_t", file="mod/lib/src/foo.c")}
        packages = gen._group_by_package(structs, {}, {})
        puml = gen.generate_module("mod", packages, [], [("mod", "other")])
        assert '"mod" ..> "other"' in puml
        assert 'package "other"' in puml
