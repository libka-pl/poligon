
import re
import string
from dataclasses import dataclass, field
from typing import Union
from pathlib import Path
import argparse
try:
    # faster implementation
    from lxml import etree
except ModuleNotFoundError:
    # standard implementation
    from xml.etree import ElementTree as etree
import polib


__author__ = 'rysson'
__version__ = '0.0.1'


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
        for lb in self:
            if lb.id == label.id:
                if lb.text is None and label.text is not None and lb.text:
                    lb.text = label.text
                elif label.text is not None:
                    assert label.text == lb.text
                lb.nodes |= label.nodes
                return lb
        self.append(label)
        return label


class Translate:
    """Whole translate process handler."""

    DEF_LANG = {c.partition('_')[0]: c for c in (
        'sq_AL', 'ar_EG', 'be_BY', 'bn_IN', 'ca_ES', 'zh_CN', 'cs_CZ', 'da_DK', 'en_GB', 'et_EE',
        'el_GR', 'iw_IL', 'hi_IN', 'in_ID', 'ga_IE', 'ja_JP', 'ko_KR', 'ms_MY', 'sr_RS', 'sl_SI',
        'sv_SE', 'uk_UA', 'vi_VN')}

    DEF_PLURAL_FORMS = 'nplurals=2; plural=(n != 1);'
    PLURAL_FORMS = {
        'cs_cz': 'nplurals=3; plural=(n==1) ? 0 : (n>=2 && n<=4) ? 1 : 2;',
        'fr_fr': 'nplurals=2; plural=(n > 1);',
        'hr_hr': 'nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<12 || n%100>14) ? 1 : 2);',
        'pl_pl': 'nplurals=3; plural=(n==1 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);',
        'ro_ro': 'nplurals=3; plural=(n==1?0:(((n%100>19)||((n%100==0)&&(n!=0)))?2:1));',
        'tr_tr': 'nplurals=1; plural=0;',
    }

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

    _RE_LABEL_NUM = re.compile('#(?P<id>\d+)')
    _RE_READ_PO = re.compile(r'(?:^|\n)(?P<var>(?:msgctxt|msgid|msgstr))[ \t]*'
                             r'(?:[ \t]*[\n]"(?P<val>(?:\.|[^"])*))+"')
    _RE_PO_VAL = re.compile(r'\s*"((?:\.|[^"])*)"')

    def __init__(self):
        self.inputs = []
        self._by_id: dict[int, Label] = {}
        self._by_text: dict[str, LabelList[Label]] = {}

    def lang_code(self, code: str):
        """Return language code like "en_US". Try guess, ex "pl" -> "pl_PL"."""
        if '_' not in code:
            try:
                code = self.DEF_LANG[code]
            except KeyError:
                code = f'{code.lower()}_{code.upper()}'
        return code

    def _scan(self, tree: etree.Element):
        """Scan single XML."""
        root = tree.getroot()
        for node in root.findall('.//*[@label]'):
            text = node.get('label')
            if text.isdigit():
                lid = int(text)
                label = self._by_id.setdefault(lid, Label(lid))
            else:
                lst = self._by_text.setdefault(text, LabelList())
                label = lst.add(Label(None, text))
            label.nodes.add(node)

    def load_input(self, path: Union[str, Path]):
        """Load XML and keep data."""
        tree = etree.parse(str(path))
        self.inputs.append(tree)
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
                    label = Label(L1.id or L2.id, L1.text or L2.text, L1.nodes | L2.nodes)
                    breakpoint()
                    ...
                #     self._by_id[label.id] = label
                #     self._by_text[label.text] = label

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
                node.set('label', str(label.id))
        for tree in self.inputs:  # XXX
            etree.dump(tree)
        # print(lid, len(self._by_id), len(self._by_text))
        # print()
        # print([L for LL in self._by_text.values() for L in LL if not L.id])
        # print([L for L in self._by_id.values() if not L.text])
        # print([L for LL in self._by_text.values() for L in LL if not L.id and len(L.nodes) > 1])

    def translate(self, lang: str, path: Union[str, Path, None] = None):
        pass


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
