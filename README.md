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
