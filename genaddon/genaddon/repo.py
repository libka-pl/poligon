
from typing import Union, Dict, Set, BinaryIO
from pathlib import Path
from dataclasses import dataclass, field
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
from io import BytesIO
from logging import getLogger
logger = getLogger('genaddon.repo')


@dataclass
class Repo:
    """Simple repo XML holder."""

    root: etree.Element = field(default_factory=lambda: etree.Element('addons'))
    keys: Dict[str, Set[str]] = field(default_factory=dict)

    def append(self, addon: 'Addon'):
        """Append addon to repo."""
        versions = self.keys.setdefault(addon.id, set())
        if addon.version in versions:
            logger.warning(f'Overrideing {addon.id}-{addon.version} by {addon.path}')
        versions.add(addon.version)
        self.root.append(addon.root)


class Addon:
    """Simple Kodi addon description."""

    Ignore = (
        '.git*',
    )

    def __init__(self, path: Union[str, Path, BinaryIO], *, remove_comments: bool = True):
        if isinstance(path, str):
            path = Path(path)
        self.path: Union[Path, BinaryIO] = path
        self._root: etree.Element = None
        self.remove_comments: bool = remove_comments

    def is_valid(self) -> bool:
        """True, if addon has "addon.xml" file."""
        path = self.path / 'addon.xml'
        return path.exists()

    def _load_root(self, file: Union[str, Path, BinaryIO] = None) -> etree.Element:
        """Load root from opened `file`."""
        if file is None:
            if isinstance(self.path, Path):
                file = self.path / 'addon.xml'
            else:
                file = self.path
        if isinstance(file, Path):
            file = str(file)
        try:
            parser = etree.XMLParser(remove_blank_text=True, remove_comments=self.remove_comments)
            xml = etree.parse(file, parser)
        except Exception:
            raise
            xml = etree.parse(file)
        root = xml.getroot()
        if root.tag != 'addon':
            raise TypeError(f'Addon {self.path} is NOT valid')
        return root

    @property
    def root(self) -> etree.Element:
        """Returns addon.xml root XML node."""
        if self._root is None:
            self._root = self._load_root()
        return self._root

    @property
    def id(self):
        return self.root.get('id')

    @property
    def version(self):
        return self.root.get('version')

    def pack(self, pool: Path, *, dry_run: bool = False):
        aid = Path(self.id)
        apath: Path = pool / aid
        zpath: Path = apath / f'{self.id}-{self.version}.zip'
        if dry_run:
            if not apath.exists():
                logger.info(f'Make directory {apath}')
            logger.info(f'Pack addon {self.id}: {self.path} -> {zpath}')
        else:
            apath.mkdir(parents=True, exist_ok=True)
            with ZipFile(zpath, 'w') as azip:
                for path in self.path.glob('**/*'):
                    if path.is_file() or path.is_symlink():
                        azip.write(path, aid / path.relative_to(self.path))
        for fname in ('addon.xml', 'icon.png', 'fanart.jpg'):
            path = self.path / fname
            if path.exists():
                if dry_run:
                    logger.debug(f' - update file {apath / fname}')
                else:
                    copy2(path, apath / fname)


def scan(*, repo: Repo, pool: Path):
    """
    Scan pool for all addon's ZIP.
    """
    for path in pool.glob('**/?*.?*-?*.zip'):
        logger.debug(f'Scanning addon {path}')
        name = path.parent.name
        with ZipFile(path) as azip:
            try:
                with azip.open(f'{name}/addon.xml') as f:
                    addon = Addon(f)
                    repo.append(addon)
            except KeyError:
                logger.error(f'Invalid archive {path}, has no {name}/addon.xml')


def generate(*paths, repo: Repo, pool: Path, dry_run: bool = False):
    """
    Gnerate repo <addons/> node from all given paths.
    Path point to addon or foler with addons.
    """
    for path in paths:
        path = Path(path)
        if (addon := Addon(path)).is_valid():
            addon.pack(pool, dry_run=dry_run)
            repo.append(addon)
        else:
            for p in path.iterdir():
                if (addon := Addon(p)).is_valid():
                    addon.pack(pool, dry_run=dry_run)
                    repo.append(addon)
    return repo


def process(*paths, pool: Union[str, Path] = None, output: Union[str, Path], signatures: str = 'sha256',
            kver: str = '19', update: bool = False, dry_run: bool = False):
    """Process paths. Generate XML and write addons.xml."""
    output = Path(output)
    if pool is not None:
        pool = Path(pool)
        if kver:
            pool /= kver
        output = pool / output
    if dry_run:
        if not output.parent.exists():
            logger.info(f'Make directory {output.parent}')
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
    repo = Repo()
    if update:
        scan(repo=repo, pool=pool)
    generate(*paths, repo=repo, pool=pool, dry_run=dry_run)
    if dry_run:
        logger.info(f'Write {output}')
        with BytesIO() as f:
            etree.ElementTree(repo.root).write(f, pretty_print=True, encoding='utf-8', xml_declaration=True)
            addons_data = f.getvalue()
    else:
        with open(output, 'wb') as f:
            etree.ElementTree(repo.root).write(f, pretty_print=True, encoding='utf-8', xml_declaration=True)
        with open(output, 'rb') as f:
            addons_data = f.read()
    for sig in signatures:
        module = getattr(hashlib, sig)
        cksum = module(addons_data).hexdigest()
        sumfile = output.with_suffix(f'{output.suffix}.{sig}')
        if dry_run:
            logger.info(f'Write checksum {sig} to {sumfile}')
        else:
            with open(sumfile, 'w') as f:
                print(cksum, end='', file=f)


def arg_parser(parser: ArgumentParser = None):
    """Main entry."""
    if parser is None:
        parser = ArgumentParser(description='Kodi repo ganerator')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--pool', '-p', default='pool', help='path to pool folder (with addons.xml and zips)')
    group.add_argument('--output', '-o', default='addons.xml', help='output addons.xml file')
    parser.add_argument('--update', '-u', action='store_true', help='update existing repo pool')
    parser.add_argument('--signature', '-s', action='append', choices=('sha512', 'sha256', 'sha1', 'md5'),
                        help='signature hash type [sha256]')
    group.add_argument('--kodi-version', '-k', default='19', help='Kodi version [19]')
    parser.add_argument('path', metavar='PATH', nargs='+', help='path to addon or folder with addons')
    return parser


def run(args: Namespace):
    """Run tool."""
    if not args.signature:
        args.signature = ['sha256']
    process(*args.path, output=args.output, signatures=args.signature, pool=args.pool, kver=args.kodi_version,
            update=args.update, dry_run=args.dry_run)


def main(argv: list[str] = None):
    """Main entry."""
    p = arg_parser()
    args = p.parse_args(argv)
    run(args)


if __name__ == '__main__':
    main()
