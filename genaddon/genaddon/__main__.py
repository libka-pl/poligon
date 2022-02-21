
import argparse
from .repo import run as repo_run, arg_parser as repo_parser


def main(argv: list[str] = None):
    """Main entry."""
    parser = argparse.ArgumentParser(description='Kodi repo ganerator')
    subparsers = parser.add_subparsers(dest='command', help='sub-command help')

    repo = subparsers.add_parser('repo', help='build repo')
    repo_parser(repo)

    args = parser.parse_args(argv)
    print(args)
    if args.command == 'repo':
        repo_run(args)


if __name__ == '__main__':
    main()
