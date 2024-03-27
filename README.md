# qc-tool

## pdm

### Installera pdm på windows och sätt upp det i din miljö

- Installera pdm i din python 3.11 installation

> C:\Program Files\Python311\python.exe -m pip install pdm

- Skapa ett venv i python 3.11

> C:\Program Files\Python311\python.exe -m venv venv

- skapa en fil som du döper till .pdm-python i qc-tool.
  Skriv in sökvägen på din dator till det venv du vill jobba i projektet
  Exempel: C:\LenaV\code\w_qc-tool\venv\Scripts\python.exe

> C:\Program Files\Python311\python.exe -m pdm install

### bygga ett wheel

> C:\Program Files\Python311\Scripts\pdm.exe build

## ruff

För att linta och formatera koden används `ruff`.

### Lintning

Linta koden med följande kommando:

```bash
$ ruff check
```

Kontrollerar att koden uppfyller konfigurerade linting-regler. Konfigurationen finns i `pyproject.yaml` under sektionen
`[tool.ruff.lint]`. Vissa identifierade problem kan `ruff` åtgärda själv. Detta görs med flaggan `--fix`.

```bash
$ ruff check --fix
```

Information om alla regler finns här:

- https://docs.astral.sh/ruff/rules/

### Formatering

Formatera koden med följande kommando:

```bash
$ ruff format
```

## pre-commit
För att hantera pre-commit-hook för git används verktyget `pre-commit`. Verktyget installeras som en del av
dev-dependencies men för att aktivera det behöver man skriva följande kommando:

```bash
$ pre-commit install
```

Efter aktivering kommer en commit att avbrytas om inte en serie av kontroller går igenom. Vilka kontroller som ingår
styrs av konfigurationen i `.pre-commit-config.yaml`.

För att kringgå kontroller (t.ex. vid commit till en topic branch) kan man lägga till flaggan `--no-verify` när man
comittar.

```bash
$ git commit --no-verify
```

