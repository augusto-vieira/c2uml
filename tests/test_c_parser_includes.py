"""
Testes do coletor de diretórios de include.

O c2uml varre a árvore de diretórios buscando pastas 'include/'
para passar como -I ao pré-processador C.
"""
import os
import pytest

from parser.c_parser import collect_include_dirs, _SKIP_DIRS


class TestColetarDiretoriosInclude:
    """collect_include_dirs varre a árvore e retorna paths de diretórios 'include/'."""

    def test_encontra_diretorios_include(self, tmp_path):
        """Detecta diretórios 'include/' dentro da árvore do projeto."""
        (tmp_path / "mod_a" / "lib" / "include").mkdir(parents=True)
        (tmp_path / "mod_b" / "lib" / "include").mkdir(parents=True)
        result = collect_include_dirs(str(tmp_path))
        assert len(result) == 2
        assert all("include" in d for d in result)

    def test_ignora_diretorios_de_build_e_venv(self, tmp_path):
        """Diretórios como venv/, build/, .git/ são ignorados na varredura."""
        for skip in _SKIP_DIRS:
            (tmp_path / skip / "include").mkdir(parents=True)
        assert collect_include_dirs(str(tmp_path)) == []

    def test_ignora_venv_mas_encontra_src(self, tmp_path):
        """venv/ é ignorado, mas src/include/ é encontrado."""
        (tmp_path / "venv" / "lib" / "include").mkdir(parents=True)
        (tmp_path / "src" / "include").mkdir(parents=True)
        result = collect_include_dirs(str(tmp_path))
        assert len(result) == 1
        assert result[0].endswith(os.path.join("src", "include"))

    def test_diretorio_vazio_retorna_lista_vazia(self, tmp_path):
        """Sem diretórios 'include/', retorna lista vazia."""
        assert collect_include_dirs(str(tmp_path)) == []

    def test_encontra_include_aninhado(self, tmp_path):
        """Encontra 'include/' mesmo em estruturas profundas."""
        (tmp_path / "a" / "b" / "c" / "include").mkdir(parents=True)
        result = collect_include_dirs(str(tmp_path))
        assert len(result) == 1
        assert result[0].endswith("include")

    def test_inclui_subdiretorios_de_include(self, tmp_path):
        """Subdiretórios de include/ (public/, private/) também são adicionados."""
        inc = tmp_path / "lib" / "include"
        (inc / "private").mkdir(parents=True)
        (inc / "public").mkdir(parents=True)
        result = collect_include_dirs(str(tmp_path))
        assert len(result) == 3
        bases = {os.path.basename(d) for d in result}
        assert bases == {"include", "private", "public"}

    def test_funciona_com_arquivo_como_entrada(self, tmp_path):
        """Aceita o diretório de um arquivo como base de busca."""
        (tmp_path / "include").mkdir()
        c_file = tmp_path / "main.c"
        c_file.write_text("int x;")
        result = collect_include_dirs(str(tmp_path))
        assert len(result) == 1
