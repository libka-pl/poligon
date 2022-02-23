
import logging
import argparse
from .repo import run as repo_run, arg_parser as repo_parser


def main(argv: list[str] = None):
    """Main entry."""
    parser = argparse.ArgumentParser(description='Kodi repo ganerator')
    parser.add_argument('--dry-run', action='store_true', help='do make no effect')
    parser.add_argument('--log-level', choices=('critical', 'error', 'warning', 'info', 'debug'),
                        default='info', help='log level')
    subparsers = parser.add_subparsers(dest='command', help='sub-command help')

    repo = subparsers.add_parser('repo', help='build repo')
    repo_parser(repo)

    args = parser.parse_args(argv)
    print(args)
    logging.basicConfig(level=getattr(logging, args.log_level.upper()))
    if args.command == 'repo':
        repo_run(args)


if __name__ == '__main__':
    main()


