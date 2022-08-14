#!/usr/bin/env python3

from pathlib import Path
import subprocess
import traceback
import argparse
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

def command_run(args):
    location = Path(args.ROOT).resolve()
    world = args.WORLD
    jar = (location / 'run' / 'server.jar').resolve()
    memory = args.memory

    java_args = '-jar -Xmx{0} -Xms{0} {1}'.format(memory, jar)
    server_args = '--nogui --universe worlds --world {0}'.format(world)
    command = f'java {java_args} {server_args}'

    print(f'Working Directory: {location}')
    print(f'Server JAR: {jar}')
    if not location.exists():
        display_error(Exception(f'Root directory "{jar}" does not exist.'))
    if not jar.exists():
        display_error(Exception(f'Server jar "{jar}" does not exist.'))

    print(f'Running Command:\n{command}')
    os.chdir(location / 'run')
    subprocess.run(command, shell=True, stdout=subprocess.DEVNULL)

def command_init(args):
    location = Path(args.ROOT).resolve()
    jar = Path(args.JAR).resolve()
    jar_name = jar.name

    if not location.exists():
        os.makedirs(location)

    if not jar.exists():
        display_error(Exception(f'Server jar "{jar}" does not exist.'))

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

def run_init_jar(location: Path, jar_name: str):
    out = open(location / 'init_jar_output.txt', 'w')
    err = open(location / 'init_jar_errors.txt', 'w')
    jar_path = location / 'run' / jar_name
    subprocess.run(['java', '-jar', jar_path, '--nogui'], stdout=out, stderr=err)

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
        display_error(e)

    print(ident, f'[✓] {description}')
    return result

def display_error(exception: Exception):
    print(f'\nFailed: {exception}')
    print('Traceback:')
    print(''.join(traceback.TracebackException.from_exception(exception).format()))
    exit(1)

def parse_args():
    parser = argparse.ArgumentParser(description='CLI utility for managing Minecraft Server Environments')
    action = parser.add_subparsers(dest='action')

    # init
    init_action = action.add_parser('init', help='initialise server environment')
    init_action.add_argument('ROOT', type=str,
                             help='path to the root (directory) of the new server environment')
    init_action.add_argument('JAR', type=str,
                             help='path to the server jar to use when unpacking')

    # run
    run_action = action.add_parser('run', help='run server environment')
    run_action.add_argument('ROOT', type=str,
                             help='path to the root (directory) of the server environment to run')
    run_action.add_argument('WORLD', type=str,
                             help='the name of the world to load (without path)')
    run_action.add_argument('--memory', type=str, default='1000M',
                             help='memory the JVM should allocate for the server, defaults to 1000M')

    return parser.parse_args(), parser

def main():
    args, parser = parse_args()

    if args.action == None:
        parser.print_help()
        exit(1)

    command_dispatch = {
        'init': command_init,
        'run': command_run,
    }

    command_dispatch[args.action](args)

if __name__ == '__main__':
    main()
