#!/usr/bin/env python3

import argparse
from collections import namedtuple
from shard_prometheus_utils import handle_install, install_parser, \
                    handle_upgrade, upgrade_parser, handle_delete, delete_parser

CommandHandler = namedtuple('CommandHandler', ['handler', 'parser'])

ops = {
    'install': CommandHandler(handle_install, install_parser),
    'upgrade': CommandHandler(handle_upgrade, upgrade_parser),
    'delete': CommandHandler(handle_delete, delete_parser)
}


    
def parse_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    subparsers = parser.add_subparsers(help='install prometheus and thanos',
            dest="subcommand")
    for key in ops:
        ops[key].parser(subparsers, key)

    return parser.parse_args()    

def main():
    args = parse_args()
    ops[args.subcommand].handler(args)

if __name__ == "__main__":
    main()
