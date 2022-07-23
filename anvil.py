#!/usr/bin/env python3

from pathlib import Path
import shutil
import typing
import sys
import os

def command_init(args: typing.List[str]):
    do_current_location = len(args) == 0
    location = Path(os.getcwd() if do_current_location else args[0]).resolve()

    if not location.exists():
        raise Exception(f'Location "{location}" does not exist')

    config = create_config(location)
    data = create_data(location)
    _ = create_run(location, data, config)

def context(name: str):
    def decorator(func):
        def wrapper(*args, **kwargs):
            location = list(args)[0] / name
            location.mkdir(exist_ok=True)

            func(location, *args[1:], **kwargs)
            return location
        return wrapper
    return decorator

@context('config')
def create_config(location: Path):
    copy_item(location, 'eula.txt')
    copy_item(location, 'server.properties')

@context('data')
def create_data(location: Path):
    (location / 'worlds').mkdir(exist_ok=True)
    (location / 'logs').mkdir(exist_ok=True)

@context('run')
def create_run(location: Path, data: Path, config: Path):
    link_item(config, location, 'eula.txt')
    link_item(config, location, 'server.properties')
    link_item(data, location, 'logs')
    link_item(data, location, 'worlds')

def copy_item(destination: Path, item: str):
    # TODO: change to anvil install location + file_name
    file_path = Path(item)
    shutil.copy(file_path, destination)

def link_item(source: Path, destination: Path, item: str):
    destination = destination / item
    source = source / item
    if not destination.exists():
        os.symlink(source, destination)

def main():
    args = sys.argv

    command_dispatch = {
        'init': command_init,
    }

    command = args[1]
    command_dispatch[command](args[2:])

if __name__ == '__main__':
    main()
