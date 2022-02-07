
from pathlib import Path
import argparse
from datetime import datetime
from itertools import chain
from lxml import etree


def human_size(size):
    units = ('B', 'KB', 'MB', 'GB', 'TB')
    for x in units:
        if size < 1024:
            return f'{size:3.1f} {x}'
        size /= 1024
    return f'{size * 1024:3.1f} {units[-1]}'


def file_size(path):
    path = Path(path)
    return path.stat().st_size


class Converter:

    OPTIONS = {'space', 'lang', 'icon', 'tag', 'timezone', 'category'}

    def __init__(self, path, *, options, output=None):
        self.path = Path(path)
        self.options = options
        if output is None:
            self.output = self.path.parent / f'{self.path.stem}.new{self.path.suffix}'
        else:
            self.output = Path(output)
        self.tree = None
        self.root: etree.Element = None
        self.by_value = {}
        self.by_id = {}

    def load(self):
        parser = etree.XMLParser(remove_blank_text=True)
        self.tree = etree.parse(str(self.path), parser)
        self.root = self.tree.getroot()

    def write(self):
        pretty_print = 'space' not in self.options
        self.tree.write(str(self.output), xml_declaration=True, encoding='utf-8', pretty_print=pretty_print)

    def shorcut(self, value):
        """Get shortcut ID for value."""
        try:
            sid = self.by_value[value]
        except KeyError:
            # find unique icon id
            hsh = hash(value)
            for i in range(4, 8):
                sid = f'{abs(hsh):x}'[:i]
                if sid not in self.by_id:
                    break
            self.by_value[value] = sid
            self.by_id[sid] = value
        return sid

    def add_shortcut_nodes(self):
        if self.by_id:
            node = self.root.find('./shortcuts')
            if node is None:
                node = etree.Element('shortcuts')
                self.root.insert(0, node)
            for sid, value in self.by_id.items():
                if node.find(f'./*[@id="{sid}"]') is None:
                    node.append(etree.Element('short', id=sid, value=value))

    def convert_lang(self):
        self.root.attrib['lang'] = 'pl'
        for node in self.root.iterfind('.//*[@lang]'):
            if node.get('lang') == 'pl':
                del node.attrib['lang']

    def convert_icon(self):
        for node in self.root.iterfind('.//icon[@src]'):
            url, sep, name = node.get('src').rpartition('/')
            if sep and url:
                iid = self.shorcut(url)
                node.attrib['src'] = f'{{{iid}}}/{name}'

    def convert_tag(self):
        for node in self.root.iterfind('./channel/display-name'):
            node.tag = 'name'
        for node in self.root.iterfind('.//programme'):
            node.tag = 'prog'

    def convert_timezone(self):
        for node in self.root.iterfind('.//programme'):
            for attr in ('start', 'stop'):
                if '+' in (node.get(attr) or ''):
                    d = datetime.strptime(node.get(attr), '%Y%m%d%H%M%S %z')
                    d = (d - d.utcoffset()).replace(tzinfo=None)
                    node.set(attr, f'{d:%Y%m%d%H%M%S})')

    def convert_category(self):
        categories = {}
        # for node in self.root.iterfind('.//programme|.//prog'):
        for node in chain(self.root.iterfind('.//programme'), self.root.iterfind('.//prog')):
            category = node.find('category')
            if category is None:
                name = None
            else:
                name = category.text
                node.remove(category)
            categories.setdefault(name, []).append(node)
            self.root.remove(node)
        for name, nodes in categories.items():
            category = etree.SubElement(self.root, 'category')
            if category is not None:
                category.set('category', name)
            category.extend(nodes)

    def process(self):
        if 'lang' in self.options:
            self.convert_lang()
        if 'icon' in self.options:
            self.convert_icon()
        if 'timezone' in self.options:
            self.convert_timezone()
        if 'tag' in self.options:
            self.convert_tag()
        if 'category' in self.options:
            self.convert_category()
        self.add_shortcut_nodes()


def split(s):
    if not s.strip():
        return set()
    options = {s.strip() for s in s.split(',')}
    if options - Converter.OPTIONS:
        msg = 'Unknown converter options: %s' % ', '.join(options - Converter.OPTIONS)
        import sys  # hack for debug
        print(msg + '\nAllowed converter options: %s' % ', '.join(Converter.OPTIONS), file=sys.stderr)
        raise ValueError(msg, 'qwe')
    return options


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('path', metavar='PATH', type=Path, help='path to EPG XML base file')
    p.add_argument('--output', '-o', metavar='PATH', type=Path, help='output path')
    p.add_argument('--convert', '-c', metavar='OPT,[OPT]...', type=split, default=Converter.OPTIONS,
                   help='what to convert: icons, spaces, lang')
    args = p.parse_args(argv)
    converter = Converter(args.path, output=args.output, options=args.convert)
    converter.load()
    converter.process()
    converter.write()
    size_before = file_size(converter.path)
    size_after = file_size(converter.output)
    print(f'File is {human_size(size_before - size_after)} smaller ({100 * size_after / (size_before or 1):.0f}%)')


if __name__ == '__main__':
    main()
