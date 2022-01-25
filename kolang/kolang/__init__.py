from __future__ import annotations

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
except ImportError:
    # standard implementation
    from xml.etree import ElementTree as etree
import polib
from .plural import plural_forms

from logging import Logger
logger = Logger('kolang')


__author__ = 'rysson'
__version__ = '0.1.2'


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
    ref: 'Label' = None


class LabelList(list):
    """Just list with smart label add."""

    def add(self, label):
        """Add label in new ID, otherwise merge."""
        for i, lb in enumerate(self):
            if lb.id is None and label.id is not None:
                lb.id = label.id  # still label ID if was None
            if lb.id == label.id or label.id is None:
                if not lb.text and label.text:
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

    _RE_LABEL_NUM = re.compile(r'#(?P<id>\d+)')
    _RE_READ_PO = re.compile(r'(?:^|\n)(?P<var>(?:msgctxt|msgid|msgstr))[ \t]*'
                             r'(?:[ \t]*[\n]"(?P<val>(?:\\.|[^"])*))+"')
    _RE_PO_VAL = re.compile(r'\s*"((?:\\.|[^"])*)"')

    def __init__(self, *, dry_run=False, stats=True, id_from=30100, handle_getLocalizedString=True,
                 mark_translated=False, mark_obsoleted=True, backup_pattern='{}~'):
        self.xml_inputs: list[XmlInput] = []
        self.py_inputs: list[PyInput] = []
        self._ids: set[int] = set()
        self._by_id: dict[int, Label] = {}
        self._by_text: dict[str, LabelList[Label]] = {}
        self.dry_run = dry_run
        self.stats = stats
        self.handle_getLocalizedString = handle_getLocalizedString
        self.id_from = id_from
        self.mark_translated = mark_translated
        self.mark_obsoleted = mark_obsoleted
        self.backup_pattern = backup_pattern

    def _add_label(self, label, *, used=True):
        """Add label to existing data (by ID and by TEXT)."""
        L1 = L2 = None
        if label is None:
            return
        if label.id is not None:
            # if lid < 30000:  # TODO: make option
            #     return
            L1 = self._by_id.setdefault(label.id, label)
        if label.text:
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
                if L1.text and L1.text != L2.text:
                    if (L2 is label or not used) and L1.id is not None:
                        # text mismatch in the same ID, force to generate new ID (or find another existing)
                        for lb in lst:
                            if lb.id is not None and lb.id != L2.id:
                                L2.id = lb.id
                                break
                        else:
                            L2.id = None  # need to generate new ID
                            L2.ref = L1
                            return L2
                    else:
                        raise ValueError(f'Label #{L2.id}: text mismatch: {L1.text!r} != {L2.text!r}')
                L2.nodes |= L1.nodes
                L2.trans.extend(L1.trans)
                self._by_id[label.id] = label = L2
        elif L1 is not None:
            label = L1
        elif L2 is not None:
            label = L2
        if used and label.id is not None:
            self._ids.add(label.id)
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
                    mid = r['id']
                    if mid is not None:
                        mid = int(mid)
                    if r['text'] is not None:
                        tr = Trans(file, start=sstart + r.start('text'), end=sstart + r.end('text'))
                        text = RS_ESC.sub(r'\1', r['text'])
                        label = Label(mid, text)
                    elif mid is not None:
                        self._ids.add(mid)  # mark as used
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
        return self.load_input(path / 'resources' / 'settings.xml')

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
            self._add_label(label, used=False)

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

        lidgen = max(self._by_id, default=self.id_from)
        for lst in self._by_text.values():
            for label in lst:
                if label.id is None:
                    label.id = nextid()
                    best = self._by_id.setdefault(label.id, label)
                    if label is not best:
                        best.nodes |= label.nodes
                        best.trans.extend(label.trans)
                    self._ids.add(label.id)
        for label in self._by_id.values():
            for node in label.nodes:
                node.set_label(str(label.id))
                self._ids.add(label.id)
        trans = sorted(((label, tr) for label in self._by_id.values() for tr in label.trans),
                       key=lambda x: -x[1].start)
        for label, tr in trans:
            fmt = f'{{before}}{tr.fmt}{{after}}'
            tr.file.data = fmt.format(before=tr.file.data[:tr.start], after=tr.file.data[tr.end:], label=label)
            self._ids.add(label.id)

    def write(self):
        if self.dry_run:
            return
        for input in self.xml_inputs:
            self._write_xml(input)
        for input in self.py_inputs:
            self._write_py(input)

    def _write_entry(self, path):
        if self.backup_pattern == '+':
            # write as new file
            return path.with_suffix(input.path.suffix + '.new')
        # backup and override
        if self.backup_pattern and self.backup_pattern != '{}':
            pat = self.backup_pattern
            if '/' not in pat and '\\' not in pat:
                pat = f'{{folder}}/{pat}'
            bak = Path(pat.format(path.name, path=path, name=path.name, ext=path.suffix[1:],
                                  directory=path.parent, folder=path.parent))
            # if not bak.is_relative_to(path.parent):
            #     ValueError('Backup path {bak} is outsiede of source {path}')
            path.rename(bak)
        return path

    def _write_xml(self, input):
        path = self._write_entry(input.path)
        input.tree.write(str(path), encoding='utf-8')

    def _write_py(self, input):
        path = self._write_entry(input.path)
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
                'tcomment': ('Kodi Media Center language file'
                             '\nAddon Name: {addon.name}'
                             '\nAddon id: {addon.id}'
                             '\nAddon Provider: {addon.provider}'),
            }
        ie = {int(r['id']): e for e in po if (r := self._RE_LABEL_NUM.fullmatch(e.msgctxt)) is not None}
        for label in self._by_id.values():
            assert label.id is not None
            if label.id not in ie:
                comment = []
                if not label.text:
                    comment.append('[empty]')
                msgstr = ''
                if label.ref is not None and label.ref.id in ie:
                    msgstr = ie[label.ref.id].msgstr
                entry = polib.POEntry(
                    msgctxt=f'#{label.id}',
                    msgid=label.text or f'#{label.id}',
                    # msgstr=label.text or '',
                    msgstr=msgstr,
                    comment=' '.join(comment),
                    # occurrences=[('welcome.py', '12'), ('anotherfile.py', '34')]
                )
                po.append(entry)
        # fake translate: copy all EN entries as translated texts
        if self.mark_translated:
            for entry in po:
                if not entry.obsolete and not entry.msgstr:
                    entry.msgstr = entry.msgid
        # remove obsolete flag if ID used again
        for entry in po:
            if entry.obsolete and (r := self._RE_LABEL_NUM.fullmatch(entry.msgctxt)) is not None:
                mid = int(r.group('id'))
                if mid in self._ids:
                    entry.obsolete = False
        # mark obsolete if ID is not used in XML nor PY
        if self.mark_obsoleted:
            for entry in po:
                if (r := self._RE_LABEL_NUM.fullmatch(entry.msgctxt)) is not None:
                    mid = int(r.group('id'))
                    if mid not in self._ids:
                        entry.obsolete = True
        if self.stats:
            N = len(po)
            ob = len(set(self._by_id) - self._ids)
            tr = sum(1 for e in po if e.msgstr)
            print(f'Language {lang}: translated: {100 * tr / (N or 1):.0f}% ({tr}/{N}), obsolete: {ob}')
        if self.dry_run:
            return
        po.save(path)


def process(inputs, *, args, langs=None, output=None, atype=None):
    trans = Translate(dry_run=args.dry_run, id_from=args.id_from, handle_getLocalizedString=args.gls,
                      mark_translated=args.mark_translated, mark_obsoleted=args.mark_obsoleted,
                      backup_pattern=args.backup_pattern)
    langs = {trans.lang_code(L) for L in langs or ()}

    addon_type = 'resources/language/resource.language.{lang_lower}/strings.po'
    skin_type = 'language/resource.language.{lang_lower}/strings.po'
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
                pattern = 'resource.language.{lang_lower}/strings.po'
        for lpath in output.glob(pattern.replace('{lang_lower}', '*')):
            lpath = lpath.resolve()
            pat = re.escape(pattern.replace('{lang_lower}', '__LANG__')).replace('__LANG__', '(.*?)').replace('/', r'[/\\]')
            r = re.fullmatch(fr'.*[/\\]{pat}', str(lpath))
            if r is not None:
                langs.add(r.group(1))

    for lang in langs:
        path = output
        if pattern:
            path = output / pattern.format(lang=lang, lang_lower=lang.lower())
        if path.exists():
            trans.load_translate(path)

    for path in inputs:
        path = Path(path)
        if path.is_dir():
            if (path / 'addon.xml').exists():
                try:
                    trans.load_settings()
                except IOError:
                    logger.info(f'No settring.xml in addon {path}')
                for p in path.glob('*.py'):
                    trans.load_input(p)
                for p in (path / 'resources' / 'lib').glob('**/*.py'):
                    trans.load_input(p)
            else:
                logger.warning(f'It is NOT an addon in {path}')
        else:
            trans.load_input(path)
    trans.scan()
    trans.generate()
    trans.write()

    for lang in langs:
        path = output
        if pattern:
            path = output / pattern.format(lang=lang, lang_lower=lang.lower())
        trans.translate(lang, path)


def main(argv=None):
    p = argparse.ArgumentParser(description='Translate tool for Kodi XML (like gettext)')
    p.add_argument('--version', action='version', version=__version__)
    p.add_argument('--type', choices=('addon', 'skin'), help='add-on folder structure')
    p.add_argument('--translation', '-t', metavar='PATH', action='append', type=Path,
                   help='path string.po or folder with it or to resource folder, default "."')
    p.add_argument('--language', '-L', metavar='LANG', action='append',
                   help='new language like "en", "en_US", "pl"')
    p.add_argument('--mark-translated', action='store_true', help='copy original string to all non-translated entries')
    p.add_argument('--remove', action='store_true', help='remove unsused translations : IGNORED')
    p.add_argument('--id-from', metavar='NUM', type=int, default=30100, help='lowest label ID (start from) [30100]')
    p.add_argument('--get-localized-string', dest='gls', action='store_true', default=True,
                   help='handle getLocalizedString() [default]')
    p.add_argument('--no-get-localized-string', dest='gls', action='store_false',
                   help='skip getLocalizedString()')
    p.add_argument('--mark-obsoleted', action='store_true', default=True,
                   help='mark non-used translations as obsoleted [default]')
    p.add_argument('--no-mark-obsoleted', dest='mark_obsoleted', action='store_false',
                   help='ignore non-used translations')
    p.add_argument('--backup-pattern', metavar='PATTERN', default='{}~', help='pattern for backup files [{}~]')
    p.add_argument('--dry-run', action='store_true', help='do not modify anything')
    p.add_argument('input', metavar='PATH', nargs='+', type=Path, help='path XML or PY file or addon folder')
    args = p.parse_args(argv)
    # print(args)
    process(args.input, output=args.translation, langs=args.language, args=args)


if __name__ == '__main__':
    main()
