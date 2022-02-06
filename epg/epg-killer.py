
from pathlib import Path
import argparse
from lxml import etree


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


if __name__ == '__main__':
    main()
