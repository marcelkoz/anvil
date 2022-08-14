#!/usr/bin/env python3

from pathlib import Path
import subprocess
import time
import traceback
import shutil
import typing
import stat
import sys
import os

ident = '  '

class Lock:
    def __init__(self, root: Path):
        self.__root = root
        # TODO: determine lock mechanism dynamically
        self.__locked = False
        self.__files = [
            'config/server.properties',
            'config/eula.txt',
        ]

        self.__file_map = list(map(lambda f: Path(self.__root, f).resolve(), self.__files))

    def lock(self):
        if not self.__locked:
            for path in self.__file_map:
                # r-- r-- ---
                os.chmod(path, 0o440)

            self.__locked = True

    def unlock(self):
        if self.__locked:
            for path in self.__file_map:
                # rw- rw- ---
                os.chmod(path, 0o660)

            self.__locked = False

def command_run(args: typing.List[str]):
    memory = 1
    world_name = args[0]
    java_args = '-jar -Xmx{0}G -Xms{0}G'.format(memory)
    server_args = '--nogui --universe worlds --world {1}'.format(world_name)

def run_init_jar(location: Path, jar_name: str):
    out = open(location / 'init_jar_output.txt', 'w')
    err = open(location / 'init_jar_errors.txt', 'w')
    jar_path = location / 'run' / jar_name
    subprocess.run(['java', '-jar', jar_path, '--nogui'], stdout=out, stderr=err)

def command_init(args: typing.List[str]):
    do_current_location = len(args) == 1
    location = Path(os.getcwd() if do_current_location else args[0]).resolve()
    jar = Path(args[1]).resolve()
    jar_name = jar.name

    if not location.exists():
        raise Exception(f'Location "{location}" does not exist')

    print(f'Working directory: {location}')
    print('Creating server environment...')

    print('Filesystem:')
    config = run_task('create config', create_config, location)
    data = run_task('create data', create_data, location)
    run_task('create run', create_run, location, data, config)

    print('Embed server:')
    lock = Lock(location)
    run_task('lock config files', lock.lock)
    run_task('copy server jar', copy_item, location / 'run', jar_name, jar.parents[0])
    prev = os.getcwd()
    os.chdir(location / 'run')
    run_task('run server jar', run_init_jar, location, jar_name)
    os.chdir(prev)
    run_task('unlock config files', lock.unlock)

    print('Server environment initialised')

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

    init_json_file(location, 'ops.json')
    init_json_file(location, 'whitelist.json')
    init_json_file(location, 'banned-ips.json')
    init_json_file(location, 'banned-players.json')

@context('data')
def create_data(location: Path):
    (location / 'worlds').mkdir(exist_ok=True)
    (location / 'logs').mkdir(exist_ok=True)

@context('run')
def create_run(location: Path, data: Path, config: Path):
    link_item(config, location, 'eula.txt')
    link_item(config, location, 'server.properties')

    link_item(config, location, 'ops.json')
    link_item(config, location, 'whitelist.json')
    link_item(config, location, 'banned-ips.json')
    link_item(config, location, 'banned-players.json')

    link_item(data, location, 'logs')
    link_item(data, location, 'worlds')

def init_json_file(destination: Path, item: str):
    file_path = destination / item
    shutil.copy(Path('./empty.json'), file_path)

def copy_item(destination: Path, item: str, source: Path = Path('.')):
    # TODO: change to anvil install location + file_name
    file_path = Path(source, item)
    shutil.copy(file_path, destination)

def link_item(source: Path, destination: Path, item: str):
    destination = destination / item
    source = source / item
    if not destination.exists():
        os.symlink(source, destination)

def run_task(description: str, func, *args):
    try:
        print(ident, f'[•] {description}', end='\r')
        result = func(*args)
    except Exception as e:
        print(ident, f'[✗] {description}')
        print(f'\nFailed: {e}')
        print('Traceback:')
        print(''.join(traceback.TracebackException.from_exception(e).format()))
        exit(1)

    print(ident, f'[✓] {description}')
    return result

def main():
    args = sys.argv

    command_dispatch = {
        'init': command_init,
        'run': command_run,
    }

    command = args[1]
    command_dispatch[command](args[2:])

if __name__ == '__main__':
    main()
