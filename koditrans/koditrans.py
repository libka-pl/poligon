# See: https://kodi.wiki/view/Add-on_settings_conversion

import re
import string
from dataclasses import dataclass, field
from collections import namedtuple
from typing import Union
from pathlib import Path
from datetime import datetime, timedelta, timezone
from itertools import chain
import argparse
try:
    # faster implementation
    from lxml import etree
except ModuleNotFoundError:
    # standard implementation
    from xml.etree import ElementTree as etree
import polib
from plural import plural_forms


__author__ = 'rysson'
__version__ = '0.0.2'


# Monkey Patching

def _BaseFile_metadata_as_entry(self):
    entry = _real_BaseFile_metadata_as_entry(self)
    try:
        comment = self.metadata_comment
    except AttributeError:
        pass
    else:
        entry.comment = comment
    return entry


_real_BaseFile_metadata_as_entry = polib._BaseFile.metadata_as_entry
polib._BaseFile.metadata_as_entry = _BaseFile_metadata_as_entry


Input = namedtuple('Input', 'path tree')


def local_now():
    tz = timezone(timedelta(seconds=round((datetime.now() - datetime.utcnow()).total_seconds())))
    return datetime.now(tz)


class SafeFormatter(string.Formatter):
    r"""
    Simple safe string formatter.
    """

    def get_field(self, field_name, args, kwargs):
        try:
            return super().get_field(field_name, args, kwargs)
        except (KeyError, AttributeError, IndexError):
            return '{%s}' % field_name, ()


@dataclass
class Label:

    id: int
    text: str = None
    nodes: set[etree.Element] = field(default_factory=set)


class LabelList(list):
    """Just list with smart label add."""

    def add(self, label):
        """Add label in new ID, otherwise merge."""
        for i, lb in enumerate(self):
            if lb.id == label.id:
                if lb.text is None and label.text is not None and lb.text:
                    lb.text = label.text
                elif label.text is not None:
                    assert label.text == lb.text
                lb.nodes |= label.nodes
                # return i
                return lb
        self.append(label)
        # return len(self) - 1
        return label


class NodeLValue:
    """Pseudo xml-node, points to node and one of old select "lvalues"."""

    def __init__(self, node, *, index):
        self.node = node
        self.index = index

    def __getattr__(self, key):
        return getattr(self.node, key)

    def set(self, key, value):
        assert key == 'label'
        lst = self.node.get('lvalues', '').split('|')
        if len(lst) < self.index:
            lst.append(value)
        else:
            lst[self.index] = value
        self.node.set('lvalues', '|'.join(lst))


class TranslateBase:
    """Whole translate process handler."""

    DEF_LANG = {c.partition('_')[0]: c for c in (
        'sq_AL', 'ar_EG', 'be_BY', 'bn_IN', 'ca_ES', 'zh_CN', 'cs_CZ', 'da_DK', 'en_GB', 'et_EE',
        'el_GR', 'iw_IL', 'hi_IN', 'in_ID', 'ga_IE', 'ja_JP', 'ko_KR', 'ms_MY', 'sr_RS', 'sl_SI',
        'sv_SE', 'uk_UA', 'vi_VN')}

    @classmethod
    def lang_code(cls, code: str):
        """Return language code like "en_US". Try guess, ex "pl" -> "pl_PL"."""
        if '_' not in code:
            try:
                code = cls.DEF_LANG[code]
            except KeyError:
                code = f'{code.lower()}_{code.upper()}'
        return code


class Translate(TranslateBase):
    """Whole translate process handler."""

    DEF_PLURAL_FORMS = 'nplurals=2; plural=(n != 1);'
    # see
    # - https://doc.qt.io/archives/qq/qq19-plurals.html
    # - http://docs.translatehouse.org/projects/localization-guide/en/latest/l10n/pluralforms.html
    PLURAL_FORMS = {TranslateBase.lang_code(p.code): p.forms for p in plural_forms}

    PO_HEADER = """# Kodi Media Center language file
# Addon Name: {addon}
# Addon id: {id}
# Addon Provider: {provider}
msgid ""
msgstr ""
"Project-Id-Version: {id}\n"
"Report-Msgid-Bugs-To: https://github.com/CastagnaIT/plugin.video.netflix\n"
"POT-Creation-Date: {date}\n"
"PO-Revision-Date: {date}\n"
"Last-Translator: {author}\n"
"Language-Team: {lang_name}\n"
"Language: {lang}\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Plural-Forms: {plural};\n"
"X-Generator: KodiTrans {__version__}\n"
"""

    # _RE_LABEL_NUM = re.compile('#(?P<id>\d+)')
    _RE_LABEL_NUM = re.compile('#(?P<id>3\d{4,})')
    _RE_READ_PO = re.compile(r'(?:^|\n)(?P<var>(?:msgctxt|msgid|msgstr))[ \t]*'
                             r'(?:[ \t]*[\n]"(?P<val>(?:\.|[^"])*))+"')
    _RE_PO_VAL = re.compile(r'\s*"((?:\.|[^"])*)"')

    def __init__(self):
        self.inputs: list[Input] = []
        self._by_id: dict[int, Label] = {}
        self._by_text: dict[str, LabelList[Label]] = {}

    def _scan(self, tree: etree.Element):
        """Scan single XML."""
        def add(text, node):
            if text.isdigit():
                lid = int(text)
                if lid < 30000:  # TODO: make option
                    return
                label = self._by_id.setdefault(lid, Label(lid))
            else:
                lst = self._by_text.setdefault(text, LabelList())
                label = lst.add(Label(None, text))
            label.nodes.add(node)

        root = tree.getroot()
        for node in chain(root.iterfind('.//heading'), root.iterfind('.//*[@label]')):
            if node.tag == 'heading':
                text = node.text
            else:
                text = node.get('label')
            add(text, node)
        for node in root.iterfind('.//*[@lvalues]'):
            breakpoint()
            for i, text in enumerate(node.get('lvalues').split('|')):
                add(text, NodeLValue(node, index=i))

    def load_input(self, path: Union[str, Path]):
        """Load XML and keep data."""
        path = Path(path)
        tree = etree.parse(str(path))
        self.inputs.append(Input(path, tree))
        self._scan(tree)
        return tree

    def load_settings(self, path: Union[str, Path, None] = None):
        path = Path(path or '')
        return self.load(path / 'resources' / 'settings.xml')

    def load_translate(self, path: Union[str, Path]):
        """Load XML and keep data."""
        pofile = polib.pofile(path)
        for entry in pofile:
            if (r := self._RE_LABEL_NUM.fullmatch(entry.msgctxt)) is None:
                lst = self._by_text.setdefault(entry.msgid, LabelList())
                lst.add(Label(None, entry.msgid))
            else:
                label = Label(int(r.group(1)), entry.msgid)
                L1 = self._by_id.setdefault(label.id, label)
                lst = self._by_text.setdefault(label.text, LabelList())
                L2 = lst.add(label)
                if L1 is not L2:
                    if L2.id is None:
                        breakpoint()
                        label = Label(L1.id or L2.id, L1.text or L2.text, L1.nodes | L2.nodes)
                        ...
                        #     self._by_id[label.id] = label
                        #     self._by_text[label.text] = label
                    else:
                        assert L1.id is None or L1.id == L2.id
                        assert L1.text is None or L1.text == L2.text
                        L2.nodes |= L1.nodes
                        self._by_id[label.id] = L2

    def scan(self):
        """Scan all loaded XML files."""
        # 1. translations (strings.po) must be loaded
        # 2. scan current inputs (xml)
        for tree in self.inputs:
            pass
        # 3. merge id and text labels
        ...  # TODO: do it

    def generate(self):
        """..."""
        def nextid():
            nonlocal lidgen
            lidgen += 1
            return lidgen

        lidgen = max(self._by_id, default=30100)
        for lst in self._by_text.values():
            for label in lst:
                if label.id is None:
                    label.id = nextid()
                    best = self._by_id.setdefault(label.id, label)
                    if label is not best:
                        best.nodes |= label.nodes
        for label in self._by_id.values():
            for node in label.nodes:
                if node.tag == 'heading':
                    node.text = str(label.id)
                else:
                    node.set('label', str(label.id))

    def write(self):
        for input in self.inputs:
            self._write_xml(input)

    def _write_xml(self, input):
        if False:
            # backup and override
            input.path.rename(input.path.with_suffix(input.path.suffix + '~'))
            input.tree.write(input.path)
        else:
            # write as new file
            input.tree.write(input.path.with_suffix(input.path.suffix + '.new'))

    def translate(self, lang: str, path: Union[str, Path, None] = None):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        now = local_now()
        if path.exists():
            po = polib.pofile(path)
        else:
            po = polib.POFile()
            po.metadata = {
                'Project-Id-Version': '1.0',
                'Report-Msgid-Bugs-To': 'dev@kodi-pl.net',
                'POT-Creation-Date': f'{now:%Y-%m-%d %H:%S%z}',
                'PO-Revision-Date': f'{now:%Y-%m-%d %H:%S%z}',
                'Last-Translator': 'KodiPL Team <dev@kodi-pl.net>',
                # 'Language-Team': 'English <yourteam@example.com>',
                'Language': lang,
                'MIME-Version': '1.0',
                'Content-Type': 'text/plain; charset=utf-8',
                'Content-Transfer-Encoding': '8bit',
                'Plural-Forms': self.PLURAL_FORMS.get(lang, self.DEF_PLURAL_FORMS),
            }
            po.metadata_args = {
                'tcomment': 'Kodi Media Center language file',
                # Addon Name: Unlock Kodi Advanced Settings
                # Addon id: script.unlock.advancedsettings
                # Addon Provider: Alex Bratchik
            }
        ids = {int(r['id']) for e in po if (r := self._RE_LABEL_NUM.fullmatch(e.msgctxt)) is not None}
        for label in self._by_id.values():
            assert label.id is not None
            if label.id not in ids:
                entry = polib.POEntry(
                    msgctxt=f'#{label.id}',
                    msgid=label.text,
                    msgstr=label.text,
                    # occurrences=[('welcome.py', '12'), ('anotherfile.py', '34')]
                )
                po.append(entry)
        po.save(path)


def process(inputs, langs=None, output=None, atype=None, remove=False):
    trans = Translate()
    langs = {trans.lang_code(L) for L in langs or ()}

    addon_type = 'resources/language/resource.language.{lang}/strings.po'
    skin_type = 'language/resource.language.{lang}/strings.po'
    output = Path(output or '')
    pattern = ''
    if output.is_dir():
        if atype == 'addon':
            pattern = addon_type
        elif atype == 'skin':
            pattern = skin_type
        else:
            if (output / 'language').is_dir():
                pattern = skin_type
            elif (output / 'resources' / 'language').is_dir():
                pattern = addon_type
            else:
                pattern = 'resource.language.{lang}/strings.po'
        for lpath in output.glob(pattern.replace('{lang}', '*')):
            lpath = lpath.resolve()
            pat = re.escape(pattern.replace('{lang}', '__LANG__')).replace('__LANG__', '(.*?)').replace('/', r'[/\\]')
            r = re.fullmatch(fr'.*[/\\]{pat}', str(lpath))
            if r is not None:
                langs.add(r.group(1))

    for path in inputs:
        trans.load_input(path)
    for lang in langs:
        path = output
        if pattern:
            path = output / pattern.format(lang=lang)
        if path.exists():
            trans.load_translate(path)
    trans.scan()
    trans.generate()
    trans.write()

    for lang in langs:
        path = output
        if pattern:
            path = output / pattern.format(lang=lang)
        trans.translate(lang, path)


def main(argv=None):
    p = argparse.ArgumentParser(description='Translate tool for Kodi XML (like gettext)')
    p.add_argument('--type', choices=('addon', 'skin'), help='add-on folder structure')
    p.add_argument('--language', '-L', metavar='LANG', action='append', help='new language')
    p.add_argument('--translation', '-t', metavar='PATH', action='append', type=Path,
                   help='path string.po or folder with it or to resource folder, default "."')
    p.add_argument('--remove', action='store_true', help='remove unsused translations')
    p.add_argument('input', metavar='PATH', nargs='+', type=Path, help='path to addon or folder with addons')
    args = p.parse_args(argv)
    print(args)
    process(args.input, output=args.translation, langs=args.language, remove=args.remove)


if __name__ == '__main__':
    main()
