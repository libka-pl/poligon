
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


def convert_icons(root):
    icon_by_url, icons_by_id = {}, {}
    for node in root.iterfind('.//icon[@src]'):
        url, sep, name = node.get('src').rpartition('/')
        if sep and url:
            try:
                iid = icon_by_url[url]
            except KeyError:
                # find unique icon id
                hsh = hash(url)
                for i in range(4, 8):
                    iid = f'{abs(hsh):x}'[:i]
                    if iid not in icons_by_id:
                        break
                icon_by_url[url] = iid
                icons_by_id[iid] = url
            node.attrib['src'] = f'{{{iid}}}/{name}'
    if icons_by_id:
        node = etree.Element('hashes')
        root.insert(0, node)
        for iid, url in icons_by_id.items():
            node.append(etree.Element('icon', id=iid, value=url))


def convert(path, output, options):
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(str(path), parser)
    root = tree.getroot()
    root.attrib['lang'] = 'pl'
    # remove lang="pl"
    if 'lang' in options:
        for node in root.iterfind('.//*[@lang]'):
            if node.get('lang') == 'pl':
                del node.attrib['lang']
    if 'icons' in options:
        convert_icons(root)
    pretty_print = 'spaces' not in options
    tree.write(str(output), xml_declaration=True, encoding='utf-8', pretty_print=pretty_print)


def split(s):
    return [s.strip() for s in s.split(',')]


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('path', metavar='PATH', type=Path, help='path to EPG XML base file')
    p.add_argument('--output', '-o', metavar='PATH', type=Path, default='out.xml', help='output path')
    p.add_argument('--convert', '-c', metavar='OPT,[OPT]...', type=split, default=['icons', 'spaces', 'lang'],
                   help='what to convert: icons, spaces, lang')
    args = p.parse_args(argv)
    convert(args.path, output=args.output, options=args.convert)
    size_before = file_size(args.path)
    size_after = file_size(args.output)
    print(f'File is {human_size(size_before - size_after)} smaller ({100 * size_after / (size_before or 1):.0f}%)')


if __name__ == '__main__':
    main()
