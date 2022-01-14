## Simple Kodi translate tool

Handle `./resources/language/resource.language.*/strings.po` and XML files.

Licence: MIT.


### Install

Clone.

Create virtual env.
```bash
python -m venv .venv
```

Activate virtual env, do it every time if you start work with the tool.
```bash
source .venv/bin/activate
```

Install dependencies.
```bash
pip instal -r requirements.txt
```

### Usage


Activate venv (every time if you start new terminal session).

Run tool
```bash
python koditrans.py --help

usage: koditrans.py [-h] [--type {addon,skin}] [--language LANG] [--translation PATH] [--remove] PATH [PATH ...]

Translate tool for Kodi XML (like gettext)

positional arguments:
  PATH                  path to addon or folder with addons

optional arguments:
  -h, --help            show this help message and exit
  --type {addon,skin}   add-on folder structure
  --language LANG, -L LANG
                        new language
  --translation PATH, -t PATH
                        path string.po or folder with it or to resource folder, default "."
  --remove              remove unsused translations
```
