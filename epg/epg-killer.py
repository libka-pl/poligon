
from pathlib import Path
import argparse
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


def convert(path, output):
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(str(path), parser)
    root = tree.getroot()
    root.attrib['lang'] = 'pl'
    for node in root.iterfind('.//*[@lang]'):
        if node.get('lang') == 'pl':
            del node.attrib['lang']

    tree.write(str(output), xml_declaration=True, encoding='utf-8', pretty_print=False)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('path', metavar='PATH', type=Path, help='path to EPG XML base file')
    p.add_argument('--output', '-o', metavar='PATH', type=Path, default='out.xml', help='output path')
    args = p.parse_args(argv)
    convert(args.path, output=args.output)
    size_before = file_size(args.path)
    size_after = file_size(args.output)
    print(f'File is {human_size(size_before - size_after)} smaller ({100 * size_after / (size_before or 1):.0f}%)')


if __name__ == '__main__':
    main()
