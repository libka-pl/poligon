
from typing import Union
from pathlib import Path
import hashlib
from zipfile import ZipFile
from shutil import copy2
from argparse import ArgumentParser, Namespace
try:
    # faster implementation
    from lxml import etree
except ModuleNotFoundError:
    # standard implementation
    from xml.etree import ElementTree as etree


class Addon:
    """Simple Kodi addon description."""

    Ignore = (
        '.git*',
    )

    def __init__(self, path: Union[str, Path], *, remove_comments=True):
        self.path = Path(path)
        self._root = None
        self.remove_comments = remove_comments

    def is_valid(self):
        """True, if addon has "addon.xml" file."""
        path = self.path / 'addon.xml'
        return path.exists()

    @property
    def root(self):
        """Returns addon.xml root XML node."""
        if self._root is None:
            path = self.path / 'addon.xml'
            try:
                parser = etree.XMLParser(remove_blank_text=True, remove_comments=self.remove_comments)
                xml = etree.parse(str(path), parser)
            except Exception:
                raise
                xml = etree.parse(str(path))
            root = xml.getroot()
            if root.tag != 'addon':
                raise TypeError(f'Addon {self.path} is NOT valid')
            self._root = root
        return self._root

    @property
    def id(self):
        return self.root.get('id')

    @property
    def version(self):
        return self.root.get('version')

    def pack(self, pool: Path):
        aid = Path(self.id)
        apath = pool / aid
        apath.mkdir(parents=True, exist_ok=True)
        with ZipFile(apath / f'{self.id}-{self.version}.zip', 'w') as azip:
            for path in self.path.glob('**/*'):
                if path.is_file() or path.is_symlink():
                    azip.write(path, aid / path.relative_to(self.path))
        for fname in ('addon.xml', 'icon.png', 'fanart.jpg'):
            path = self.path / fname
            if path.exists():
                copy2(path, apath / fname)


def generate(*paths, pool: Path):
    """
    Gnerate repo <addons/> node from all given paths.
    Path point to addon or foler with addons.
    """
    repo = etree.Element('addons')
    for path in paths:
        path = Path(path)
        if (addon := Addon(path)).is_valid():
            addon.pack(pool)
            repo.append(addon.root)
        else:
            for p in path.iterdir():
                if (addon := Addon(p)).is_valid():
                    addon.pack(pool)
                    repo.append(addon.root)
    return repo


def process(*paths, pool: Union[str, Path] = None, output: Union[str, Path], signatures: str ='sha256',
            kver: str = '19'):
    """Process paths. Generate XML and write addons.xml."""
    output = Path(output)
    if pool is not None:
        pool = Path(pool)
        if kver:
            pool /= kver
        output = pool / output
    output.parent.mkdir(parents=True, exist_ok=True)
    repo = generate(*paths, pool=pool)
    with open(output, 'wb') as f:
        etree.ElementTree(repo).write(f, pretty_print=True, encoding='utf-8', xml_declaration=True)
    with open(output, 'rb') as f:
        addons_data = f.read()
    for sig in signatures:
        module = getattr(hashlib, sig)
        cksum = module(addons_data).hexdigest()
        sumfile = output.with_suffix(f'{output.suffix}.{sig}')
        with open(sumfile, 'w') as f:
            print(cksum, end='', file=f)


def arg_parser(parser: ArgumentParser = None):
    """Main entry."""
    if parser is None:
        parser = ArgumentParser(description='Kodi repo ganerator')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--pool', '-p', default='pool', help='path to pool folder (with addons.xml and zips)')
    group.add_argument('--output', '-o', default='addons.xml', help='output addons.xml file')
    parser.add_argument('--signature', '-s', action='append', choices=('sha512', 'sha256', 'sha1', 'md5'),
                        help='signature hash type [sha256]')
    group.add_argument('--kodi-version', '-k', default='19', help='Kodi version [19]')
    parser.add_argument('path', metavar='PATH', nargs='+', help='path to addon or folder with addons')
    return parser


def run(args: Namespace):
    """Run tool."""
    if not args.signature:
        args.signature = ['sha256']
    process(*args.path, output=args.output, signatures=args.signature, pool=args.pool, kver=args.kodi_version)


def main(argv: list[str] = None):
    """Main entry."""
    p = arg_parser()
    args = p.parse_args(argv)
    run(args)


if __name__ == '__main__':
    main()
