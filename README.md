# qc-tool

## Setup
### uv

#### Installera uv på Windows

```bash
$ powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### Installera på MacOS / Linux
```bash
$ curl -LsSf https://astral.sh/uv/install.sh | sh
```

### ruff

För att linta och formatera koden används `ruff`.

#### Lintning

Linta koden med följande kommando:

```bash
$ uv run ruff check
```

Kontrollerar att koden uppfyller konfigurerade linting-regler. Konfigurationen finns i `pyproject.yaml` under sektionen
`[tool.ruff.lint]`. Vissa identifierade problem kan `ruff` åtgärda själv. Detta görs med flaggan `--fix`.

```bash
$ uv run ruff check --fix
```

Information om alla regler finns här:

- https://docs.astral.sh/ruff/rules/

#### Formatering

Formatera koden med följande kommando:

```bash
$ uv run ruff format
```

### pre-commit
För att hantera pre-commit-hook för git används verktyget `pre-commit`. Verktyget installeras som en del av
dev-dependencies men för att aktivera det behöver man skriva följande kommando:

```bash
$ uv run pre-commit install
```

Efter aktivering kommer en commit att avbrytas om inte en serie av kontroller går igenom. Vilka kontroller som ingår
styrs av konfigurationen i `.pre-commit-config.yaml`.

För att kringgå kontroller (t.ex. vid commit till en topic branch) kan man lägga till flaggan `--no-verify` när man
comittar.

```bash
$ git commit --no-verify
```

## Om programarkitekturen
qc-tool är designat enligt en modell som heter Model View Controller (MVC). MVC delar upp ett program i tre olika
sorters komponenter: Model, View och Controller.

### Model
En modell kapsalar in data och applikationes tillstånd (state). Fildata som har lästs in, om användaren har gjort några
val etc.

En modell få aldrig känna till något om vyer eller kontroller men kan känna till andra modeller.


### View
En vy representerar grafiskska element i applikationen och ska helst ha så lite logik som möjligt. En vy definierar HUR
saker ska ritas ut och den använder sig av modeller för VAD som ska ritas ut. 

En vy får bara ha en kontroller men kan dock ha flera modeller. 

En vy kan skapa sina egna undervyer. Detta gör det enkelt att dela upp en vy i flera delar.

### Controller
En controller är ansvarig för all affärslogik och hanterar interaktioner mellan modeller och vyer.

En controller kan noll till flera vyer men mer än en vy är sällan önskvärt.


### Signaler
Mycket av applikationens flöde styrs genom signaler som skickas från modeller. Vare modell definierar sina egna signaler
som den sedan skickar vid olika tillfällen. Exempelvis skickar `FileModel` signalen `NEW_DATA` så fort den har sparar nyinläst
data och `VisitsModel` skickar signalen `VISIT_SELECTED` så fort den sparat att en ny visit har valts. Sedan är det upp
till controllers att lyssna efter signaler de är intresserade av. Exempelvis lyssnar `VisitsController` efter `NEW_DATA`
så att den kan läsa ut vilka visits som finns i det nya datat och `MapController` lyssnar efter `VISIT_SELECTED` så att
den kan säga åt `MapView` att den ska markera den visiten på kartan.

För att lyssna på en signal anropar den lyssnande controllern modellens `register_listener`-metod och ger den en
callback-funktion som ska anropas när signalen skickas.

```python
import SimpleModel


class SimpleController:
    def __init__(self, simple_model: SimpleModel):
        self._simple_model = simple_model
        self._simple_model.register_listener(
            SimpleModel.SOMETHING_HAS_HAPPENED,
            self._on_something_has_happened
        )
    
    def _on_something_has_happened(self):
        """Denna metod kommer att anropas varje gång signalen
        SOMETHING_HAS_HAPPENED skickas från simple_model."""
        print("Something has happened!")
```

### Dependency injection
En annan viktig princip i qc-tool är det som kallas *dependency injection*. Detta innebär att om en komponent har ett
beroende av en annan komponent (exempelvis en controller som behöver en model) så skickas man in beroendet när
komponenten skapas istället för att komponenten skapar sit beroende själv.

I exemplet ovan skickas en instans av `SimpleModel` in när man skapar `SimpleController`. Om man vid ett senare
tillfälle kommer på att `SimpleController` behöver jobba med ytterligare en model, `AnotherModel`, så är det bara att se
till att den också skickas in. Av dettta följer att en komponents beroenden skapas utanför komponenten själv.
Exempelvis skapas alla modeller upp i `AppState` så fort programmet startar.

```python
import AnotherModel
import SimpleModel


class SimpleController:
    def __init__(self, simple_model: SimpleModel, another_model: AnotherModel):
        self._simple_model = simple_model
        self._simple_model.register_listener(
            SimpleModel.SOMETHING_HAS_HAPPENED,
            self._on_something_has_happened
        )
        
        self._another_model = another_model
    
```
