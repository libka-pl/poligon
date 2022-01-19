# See: https://kodi.wiki/view/Add-on_settings_conversion
#
# These IDs are reserved by Kodi:
# - strings 30000 thru 30999 reserved for plugins and plugin settings
# - strings 31000 thru 31999 reserved for skins
# - strings 32000 thru 32999 reserved for scripts
# - strings 33000 thru 33999 reserved for common strings used in add-ons

import re
import string
from dataclasses import dataclass, field
from collections import namedtuple
from typing import Union
from pathlib import Path
from datetime import datetime, timedelta, timezone
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
__version__ = '0.0.4'


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


XmlInput = namedtuple('XmlInput', 'path tree')


@dataclass
class PyInput:
    path: Path
    data: str


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


#: Source file (.py) translate info
Trans = namedtuple('Trans', 'file start end fmt', defaults=('{label.id}',))


@dataclass
class Label:
    """Single label occurace in xml or py."""

    id: int
    text: str = None
    nodes: set[etree.Element] = field(default_factory=set)
    trans: list[Trans] = field(default_factory=list)


class LabelList(list):
    """Just list with smart label add."""

    def add(self, label):
        """Add label in new ID, otherwise merge."""
        for i, lb in enumerate(self):
            if lb.id is None and label.id is not None:
                lb.id = label.id  # still label ID if was None
            if lb.id == label.id or label.id is None:
                if lb.text is None and label.text is not None and lb.text:
                    lb.text = label.text
                elif label.text is not None:
                    assert label.text == lb.text
                lb.nodes |= label.nodes
                lb.trans.extend(label.trans)
                # return i
                return lb
        self.append(label)
        # return len(self) - 1
        return label


class NodeValue:
    """Pseudo xml-node, points to node and one of old select "lvalues"."""

    def __init__(self, node, attr, *, index=None):
        self.node = node
        self.attr = attr
        self.index = index

    def __getattr__(self, key):
        return getattr(self.node, key)

    def set_label(self, value):
        if self.attr is None:
            self.node.text = value
        elif self.attr == 'lvalues':
            lst = self.node.get(self.attr, '').split('|')
            if len(lst) < self.index:
                lst.append(value)
            else:
                lst[self.index] = value
            self.node.set(self.attr, '|'.join(lst))
        else:
            self.node.set(self.attr, value)


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
    _RE_LABEL_NUM = re.compile('#(?P<id>\d+)')
    _RE_READ_PO = re.compile(r'(?:^|\n)(?P<var>(?:msgctxt|msgid|msgstr))[ \t]*'
                             r'(?:[ \t]*[\n]"(?P<val>(?:\\.|[^"])*))+"')
    _RE_PO_VAL = re.compile(r'\s*"((?:\\.|[^"])*)"')

    def __init__(self):
        self.xml_inputs: list[XmlInput] = []
        self.py_inputs: list[PyInput] = []
        self._by_id: dict[int, Label] = {}
        self._by_text: dict[str, LabelList[Label]] = {}
        self.handle_getLocalizedString = True

    def _add_label(self, label):
        """Add label to existing data (by ID and by TEXT)."""
        L1 = L2 = None
        if label is None:
            return
        if label.id is not None:
            # if lid < 30000:  # TODO: make option
            #     return
            L1 = self._by_id.setdefault(label.id, label)
        if label.text is not None:
            lst = self._by_text.setdefault(label.text, LabelList())
            L2 = lst.add(label)
        if L1 is not None and L2 is not None and L1 is not L2:
            if L2.id is None:
                breakpoint()
                label = Label(L1.id or L2.id, L1.text or L2.text, L1.nodes | L2.nodes, L1.trans + L2.trans)
                self._by_id[label.id] = label
                lst[lst.index[L2]] = label
            else:
                assert L1.id is None or L1.id == L2.id
                assert L1.text is None or L1.text == L2.text
                L2.nodes |= L1.nodes
                L2.trans.extend(L1.trans)
                self._by_id[label.id] = label = L2
        elif L1 is not None:
            label = L1
        elif L2 is not None:
            label = L2
        return label

    def _scan_xml(self, tree: etree.Element):
        """Scan single XML."""
        def add(text, node):
            if text.isdigit():
                label = Label(int(text))
            else:
                label = Label(None, text)
            if label is not None:
                label.nodes.add(node)
                self._add_label(label)

        root = tree.getroot()
        for node in root.iterfind('.//heading'):
            add(node.text, NodeValue(node, None))
        for attr in ('label', 'help'):
            for node in root.iterfind(f'.//*[@{attr}]'):
                add(node.get(attr), NodeValue(node, attr))
        for node in root.iterfind('.//*[@lvalues]'):
            for i, text in enumerate(node.get('lvalues').split('|')):
                add(text, NodeValue(node, 'lvalues', index=i))

    def load_xml(self, path: Union[str, Path]):
        """Load XML and keep data."""
        path = Path(path)
        tree = etree.parse(str(path))
        self.xml_inputs.append(XmlInput(path, tree))
        self._scan_xml(tree)
        return tree

    def load_py(self, path: Union[str, Path]):
        """Load strings from Python source and keep data."""
        def rstr(name='str'):
            pat = '|'.join((
                fr'"""(?P<{name}1>(?:\\.|.)*?)"""',   # """..."""
                fr"'''(?P<{name}2>(?:\\.|.)*?)'''",   # '''...'''
                fr'"(?P<{name}3>(?:\\.|[^"])*)"',     # "..."
                fr"'(?P<{name}4>(?:\\.|[^'])*)'",     # '...'
            ))
            return f'(?:{pat})'

        def rval(r, name='str'):
            for i in range(4):
                if (s := r[f'{name}{i+1}']) is not None:
                    return s

        def rstart(r, name='str'):
            for i in range(4):
                if (s := r.start(f'{name}{i+1}')) != -1:
                    return s

        with open(path) as f:
            data = f.read()
        file = PyInput(path, data)
        self.py_inputs.append(file)

        _R_CM = r'#\s*(?P<comment>.*)'
        _R_LL = fr'\b(?P<label>LL?)\s*(?P<label_bracket>\()\s*(?:(?P<mid>\d+)\s*,\s*)?{rstr("msg")}\s*\)'
        pat = f'{_R_CM}|{rstr()}|{_R_LL}'
        if self.handle_getLocalizedString:
            pat += fr'|\bgetLocalizedString\s*\((?P<gls>\s*(?:(?P<gls_id>\d+)|{rstr("gls_text")})\s*)\)'
        R = re.compile(pat)
        RS = re.compile(r'\$LOCALIZE\[(?:(?P<id>\d+)|(?P<text>(?:[\\%].|\[(?:[\\%].|[^]])*\]|[^]])+))\]')
        RS_ESC = re.compile(r'[\\%](.)')
        for r in R.finditer(data):
            if r['comment'] is not None:  # skip comments
                continue
            label = tr = None
            s, msg = rval(r), rval(r, 'msg')
            sstart = rstart(r)
            # L()
            if msg is not None:
                mid = r['mid']
                if mid is None:
                    offset = r.end('label_bracket')
                    tr = Trans(file, start=offset, end=offset, fmt='{label.id}, ')
                else:
                    mid = int(mid)
                    tr = Trans(file, start=r.start('mid'), end=r.end('mid'))
                label = Label(mid, msg)
            # " $LOCALIZE[] "
            elif s is not None:
                for r in RS.finditer(s):
                    if r['text'] is not None:
                        mid = r['id']
                        if mid is not None:
                            mid = int(mid)
                        tr = Trans(file, start=sstart + r.start('text'), end=sstart + r.end('text'))
                        text = RS_ESC.sub(r'\1', r['text'])
                        label = Label(mid, text)
            # getLocalizedString()
            elif r['gls'] is not None:
                mid = r['gls_id']
                if mid is None:
                    tr = Trans(file, start=r.start('gls'), end=r.end('gls'))
                else:
                    mid = int(mid)
                label = Label(mid, rval(r, 'gls_text'))
            if label is not None:
                if tr is not None:
                    label.trans.append(tr)
                self._add_label(label)

    def load_input(self, path: Union[str, Path]):
        """Load file (XML / py) and keep data."""
        path = Path(path)
        if path.suffix == '.py':
            return self.load_py(path)
        return self.load_xml(path)

    def load_settings(self, path: Union[str, Path, None] = None):
        path = Path(path or '')
        return self.load(path / 'resources' / 'settings.xml')

    def load_translate(self, path: Union[str, Path]):
        """Load XML and keep data."""
        pofile = polib.pofile(path)
        for entry in pofile:
            text = entry.msgid
            if self._RE_LABEL_NUM.fullmatch(text) and '[empty]' in entry.comment:
                text = None
            if (r := self._RE_LABEL_NUM.fullmatch(entry.msgctxt)) is None:
                label = Label(None, entry.msgid)
            else:
                label = Label(int(r.group(1)), entry.msgid)
            self._add_label(label)

    def scan(self):
        """Scan all loaded XML files."""
        # 1. translations (strings.po) must be loaded
        # 2. scan current inputs (xml)
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
                node.set_label(str(label.id))
        trans = sorted(((label, tr) for label in self._by_id.values() for tr in label.trans),
                       key=lambda x: -x[1].start)
        for label, tr in trans:
            fmt = f'{{before}}{tr.fmt}{{after}}'
            tr.file.data = fmt.format(before=tr.file.data[:tr.start], after=tr.file.data[tr.end:], label=label)

    def write(self):
        for input in self.xml_inputs:
            self._write_xml(input)
        for input in self.py_inputs:
            self._write_py(input)

    def _write_xml(self, input):
        if False:
            # backup and override
            input.path.rename(input.path.with_suffix(input.path.suffix + '~'))
            input.tree.write(input.path)
        else:
            # write as new file
            input.tree.write(input.path.with_suffix(input.path.suffix + '.new'))

    def _write_py(self, input):
        if False:
            # backup and override
            input.path.rename(input.path.with_suffix(input.path.suffix + '~'))
            path = input.path
        else:
            # write as new file
            path = input.path.with_suffix(input.path.suffix + '.new')
        with open(path, 'w') as f:
            f.write(input.data)

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
                comment = []
                if not label.text:
                    comment.append('[empty]')
                entry = polib.POEntry(
                    msgctxt=f'#{label.id}',
                    msgid=label.text or f'#{label.id}',
                    msgstr=label.text or '',
                    comment=' '.join(comment),
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
    # p.add_argument('--remove', action='store_true', help='remove unsused translations')
    p.add_argument('input', metavar='PATH', nargs='+', type=Path, help='path to addon or folder with addons')
    args = p.parse_args(argv)
    print(args)
    process(args.input, output=args.translation, langs=args.language, remove=args.remove)


if __name__ == '__main__':
    main()
