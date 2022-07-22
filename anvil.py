#!/usr/bin/env python3

from pathlib import Path
import typing
import sys
import os

def command_init(args: typing.List[str]):
    do_current_location = len(args) == 0
    location = Path(os.getcwd() if do_current_location else args[0])

    create_config(location)
    create_run(location)
    create_data(location)

def create_config(location: Path):
    pass

def create_run(location: Path):
    pass

def create_data(location: Path):
    pass

def main():
    args = sys.argv

    command_dispatch = {
        'init': command_init,
    }

    command = args[0]
    command_dispatch[command](args[1:])

if __name__ == '__main__':
    main()
