from __future__ import annotations

from typing import Union, Dict, List, Set, BinaryIO
from pathlib import Path
from dataclasses import dataclass, field
import hashlib
from fnmatch import fnmatch
from zipfile import ZipFile
from shutil import copy2
from distutils.version import LooseVersion
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
    addons: List['Addon'] = field(default_factory=list)
    keys: Dict[str, Set[str]] = field(default_factory=dict)
    old: Dict[str, str] = field(default_factory=dict)
    changed: bool = False

    def append(self, addon: 'Addon', *, old: bool = False):
        """Append addon to repo."""
        versions = self.keys.setdefault(addon.id, set())
        if addon.version in versions:
            if addon.packed:
                logger.warning(f'Overriding {addon.id}-{addon.version} by {addon.path}')
            for node in self.root:
                if node.tag == 'addon' and node.get('id') == addon.id and node.get('version') == addon.version:
                    self.root.remove(node)
                    break
        versions.add(addon.version)
        self.root.append(addon.root)
        self.addons.append(addon)
        if old:
            if LooseVersion(addon.version) > LooseVersion(self.old.setdefault(addon.id, addon.version)):
                self.old[addon.id] = addon.version

    def filter(self):
        """Filter addons, to remove older versions."""
        addons = {}
        for aname, versions in self.keys.items():
            versions = sorted(versions, key=LooseVersion)
            logger.debug(f'{aname} vers:   {versions}')
            logger.debug(f'{aname} remove: {versions[:-1]}')
            if versions:
                addons[aname] = versions[-1]
            for aver in versions[:-1]:
                node = self.root.find(f'./addon[@id="{aname}"]')  # hmm... [@id="" and @version=""] fails
                if node is None and node.get('verison') == aver:
                    logger.error(f'Can NOT find node {aname!r} {aver!r}')
                else:
                    logger.debug(f'Removing old addon {aname!r} {aver!r}')
                    self.root.remove(node)
        return addons


class Addon:
    """Simple Kodi addon description."""

    Ignore = (
        '.git*',
    )

    def __init__(self, path: Union[str, Path, BinaryIO], *, remove_comments: bool = True, ignore: List[str] = None):
        if isinstance(path, str):
            path = Path(path)
        self.path: Union[Path, BinaryIO] = path
        self._root: etree.Element = None
        self.remove_comments: bool = remove_comments
        self.ignore = [*self.Ignore, *(ignore or ())]
        self.packed = False

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

    def is_ignored(self, path):
        rel = path.relative_to(self.path)
        for pat in self.ignore:
            if pat.startswith('/'):
                if rel.parts and fnmatch(rel.parts, pat):
                    return True
            else:
                if any(fnmatch(part, pat) for part in rel.parts):
                    return True
        return False

    def pack(self, pool: Path, *, dry_run: bool = False, force: bool = False):
        aid = Path(self.id)
        apath: Path = pool / aid
        zpath: Path = apath / f'{self.id}-{self.version}.zip'
        if dry_run:
            if not apath.exists():
                logger.info(f'Make directory {apath}')
            logger.info(f'Pack addon {self.id}: {self.path} -> {zpath}')
        else:
            apath.mkdir(parents=True, exist_ok=True)
            if not force and zpath.exists():
                logger.info(f'Package {zpath} already exists.')
            else:
                with ZipFile(zpath, 'w') as azip:
                    for path in self.path.glob('**/*'):
                        if path.is_file() or path.is_symlink():
                            if self.is_ignored(path):
                                logger.debug(f'Ignore {path} file')
                            else:
                                azip.write(path, aid / path.relative_to(self.path))
                self.packed = True
        # for fname in ('icon.png', 'fanart.jpg'):
        for xpath in ('./extension/assets/icon', './extension/assets/fanart'):
            node = self.root.find(xpath)
            if node is not None and node.text:
                fname = node.text
                path = self.path / fname
                if path.exists():
                    if dry_run:
                        logger.debug(f' - update file {apath / fname}')
                    else:
                        dest = apath / fname
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        copy2(path, dest)


def scan(*, repo: Repo, pool: Path, ignore: List[str] = None):
    """
    Scan pool for all addon's ZIP.
    """
    for path in pool.glob('**/?*.?*-?*.zip'):
        logger.debug(f'Scanning addon {path}')
        name = path.parent.name
        with ZipFile(path) as azip:
            try:
                with azip.open(f'{name}/addon.xml') as f:
                    addon = Addon(f, ignore=ignore)
                    repo.append(addon, old=True)
            except KeyError:
                logger.error(f'Invalid archive {path}, has no {name}/addon.xml')


def generate(*paths, repo: Repo, pool: Path, ignore: List[str] = None, dry_run: bool = False,
             force: bool = False):
    """
    Gnerate repo <addons/> node from all given paths.
    Path point to addon or foler with addons.
    """
    for path in paths:
        path = Path(path)
        if (addon := Addon(path, ignore=ignore)).is_valid():
            addon.pack(pool, dry_run=dry_run, force=force)
            repo.append(addon)
        else:
            for p in path.iterdir():
                if (addon := Addon(p, ignore=ignore)).is_valid():
                    addon.pack(pool, dry_run=dry_run, force=force)
                    repo.append(addon)
    return repo


def process(*paths, pool: Union[str, Path] = None, output: Union[str, Path], signatures: str = 'sha256',
            ignore: List[str] = None, kver: str = '19', update: bool = False, dry_run: bool = False,
            force: bool = False):
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
    generate(*paths, repo=repo, pool=pool, dry_run=dry_run, force=force)
    new_addons = repo.filter()
    if not force and new_addons == repo.old and all(not a.packed for a in repo.addons):
        logger.info('Nothing changed in repo, skipping.')
        return
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
    parser.add_argument('--pool', '-p', default='pool', help='path to pool folder (with addons.xml and zips)')
    parser.add_argument('--output', '-o', default='addons.xml', help='output addons.xml file')
    parser.add_argument('--update', '-u', action='store_true', help='update existing repo pool')
    parser.add_argument('--signature', '-s', action='append', choices=('sha512', 'sha256', 'sha1', 'md5'),
                        help='signature hash type [sha256]')
    parser.add_argument('--force', '-f', action='store_true', help='Force regenerate zip packages')
    parser.add_argument('--ignore', '-i', action='append', help='Pattern to ignore file [.git*]')
    parser.add_argument('--kodi-version', '-k', default='19', help='Kodi version [19]')
    parser.add_argument('path', metavar='PATH', nargs='+', help='path to addon or folder with addons')
    return parser


def run(args: Namespace):
    """Run tool."""
    if not args.signature:
        args.signature = ['sha256']
    process(*args.path, output=args.output, signatures=args.signature, pool=args.pool, kver=args.kodi_version,
            ignore=args.ignore, update=args.update, dry_run=args.dry_run, force=args.force)


def main(argv: list[str] = None):
    """Main entry."""
    p = arg_parser()
    args = p.parse_args(argv)
    run(args)


if __name__ == '__main__':
    main()
