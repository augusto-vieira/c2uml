# c2uml

Gera diagramas de classes PlantUML a partir de código C.

Analisa arquivos `.c` e `.h`, extrai structs, enums, callbacks, funções e relações entre módulos, e produz um `.puml` pronto para visualização.

## Instalação

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

No Linux, para gerar PNG/SVG é necessário o PlantUML:

```bash
sudo apt install plantuml
```

## Uso

Analisar um diretório inteiro (structs + relações):

```bash
python -m cli.main examples --mode full
```

Analisar um arquivo específico com saída customizada:

```bash
python -m cli.main examples/pessoa.h -o pessoa.puml
```

Gerar PNG automaticamente:

```bash
python -m cli.main examples --mode full --png
```

Gerar SVG (recomendado para projetos grandes — vetorial, sem corte, com zoom):

```bash
python -m cli.main examples --mode full --svg
```

Gerar um diagrama por módulo (recomendado para projetos grandes):

```bash
python -m cli.main examples/sat --mode module -o output/
```

Gera um `.puml` por pacote no diretório de saída, cada um com suas dependências externas. Combine com `--svg` ou `--png`:

```bash
python -m cli.main examples/sat --mode module -o output/ --svg
python3 -m cli.main examples/sat --mode module -o output/ --svg --quiet
```

Gerar apenas structs (sem relações):

```bash
python -m cli.main examples --mode structs
```

Gerar diagrama de dependências entre pacotes (visão macro):

```bash
python -m cli.main examples/sat --mode deps -o deps.puml --svg
```

Filtrar por um módulo específico (mostra o pacote + dependências externas):

```bash
python -m cli.main examples/sat --filter sat_tcp -o sat_tcp.puml --svg
```

### Opções

| Argumento       | Descrição                                      | Padrão         |
|-----------------|-------------------------------------------------|----------------|
| `input`         | Arquivo `.c`/`.h` ou diretório para analisar   | (obrigatório)  |
| `-o`, `--output`| Caminho do `.puml` ou diretório (mode module)  | `structs.puml` |
| `--mode`        | `full`, `structs`, `module` ou `deps`          | `full`         |
| `--filter`      | Mostra apenas este pacote e suas dependências  | desativado     |
| `--png`         | Gera PNG via `plantuml` após gerar o `.puml`   | desativado     |
| `--svg`         | Gera SVG via `plantuml` após gerar o `.puml`   | desativado     |
| `--quiet`       | Suprime warnings, mostra apenas resumo          | desativado     |
| `--all-deps`    | Mostra todas as dependências (incluindo transitivas) | desativado     |
| `--init`        | Gera um `.c2uml.yaml` template no diretório atual   | —              |

## Dependências entre módulos

O c2uml detecta automaticamente a melhor fonte de dependências:

- **Com CMakeLists.txt** → usa `target_link_libraries` como fonte (dependências declaradas no build system)
- **Sem CMakeLists.txt** → infere pelos `#include` e aplica redução transitiva (remove dependências indiretas)

Use `--all-deps` para desativar a filtragem e ver todas as dependências (incluindo transitivas).

## Configuração — `.c2uml.yaml`

Gere um template comentado com:

```bash
python -m cli.main --init
```

Ou coloque um arquivo `.c2uml.yaml` na raiz do diretório analisado para customizar o comportamento:

```yaml
# Diretórios de include extras
include_dirs:
  - vendor/include

# Regras de agrupamento em pacotes
packages:
  markers:
    - lib
    - include
    - src
  rules:
    - pattern: "*/modules/main/*"
      name: "core"
    - pattern: "*/drivers/*"
      name: "drivers"

# Visibilidade (+ público, - privado)
visibility:
  public:
    - "include/public/"
    - "include/api/"
  private:
    - "include/private/"
    - "src/internal/"

# Arquivos a ignorar (glob patterns)
exclude:
  - "test_*"
  - "*_sample.c"
  - "vendor/"
```

Sem o arquivo, o c2uml usa defaults sensatos (infere pacotes pela estrutura de diretórios, visibilidade por `include/public/` e `include/private/`).

Por padrão, os diretórios `samples/`, `tests/`, `test/` e `examples/` são excluídos. As exclusões do `.c2uml.yaml` são somadas a esses defaults.

Exemplo: com o `.c2uml.yaml` acima em `examples/sat/`, rode:

```bash
python -m cli.main examples/sat --mode module -o output/ --svg
```

O c2uml detecta o arquivo automaticamente, aplica as exclusões e regras de pacote, e gera um diagrama SVG por módulo.

## O que é extraído

- **Structs** → classes com atributos e métodos associados
- **Enums** → classes `<<enumeration>>` com valores
- **Callbacks** (function pointers) → `<<interface>>` com assinatura `invoke(...)`
- **Relações** → composição (`*--`), associação (`-->`), herança (`--|>`) entre structs
- **Unions** → classes `<<union>>` com membros
- **Macros** → macros-função viram métodos (`: macro`), constantes `#define` viram atributos (`: const`)
- **Dependências entre módulos** → via `#include` entre headers do projeto (`..>`)
- **Relações de uso** → chamadas de função entre módulos nos `.c` (`..>`)
- **Visibilidade** → headers em `include/public/` geram `+`, em `include/private/` geram `-`
- **Encapsulamento C** → funções `static` e funções definidas só no `.c` geram `-` (privado)
- **Ponteiros opacos** → `typedef struct X X;` sem corpo geram `<<opaque>>`
- **Structs aninhadas** → structs nomeadas dentro de structs viram classes separadas com composição
- **Pacotes** → agrupamento automático por módulo com hierarquia (`builtin`/`optionals`)
- **Estereótipos de métodos** → `<<create>>` para `_create`/`_init`/`_open`, `<<destroy>>` para `_destroy`/`_close`/`_free`

## Viewer interativo

No modo `module` com `--svg`, o c2uml gera um viewer HTML por módulo com:

- **Collapse/Expand** — alterna entre diagrama completo e colapsado (só nomes das classes)
- **Popup de classe** — no modo colapsado, clique numa classe para ver atributos e métodos
- **Sidebar** — lista de classes com busca, dependências e "used by" com links de navegação
- **Hyperlinks** — pacotes de dependência são clicáveis, navegam para o diagrama do módulo
- **Legenda** — botão ℹ na toolbar abre modal com a legenda de cores, ícones e setas
- **Index** — página principal com busca por módulo ou por classe

## Testes

```bash
pytest
```

## Arquitetura

```
parser/          → Parsing de arquivos C via pycparser
analyzer/        → Constrói modelos (structs, enums, callbacks, funções, relações) a partir da AST
domain/          → Dataclasses: StructModel, FunctionModel, RelationModel, EnumModel, CallbackModel
generator/       → Gera saída PlantUML, viewer HTML interativo e index
config/          → Carregamento de .c2uml.yaml e configuração
utils/           → Carregamento de arquivos .c/.h
cli/             → Ponto de entrada via linha de comando
tests/           → Testes automatizados
```
