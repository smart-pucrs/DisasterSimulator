import json
import os
import pathlib
import argparse
import multiprocessing
import subprocess


root = pathlib.Path(__file__).parent.absolute()
default_events_path = 'default_events.txt'


def start_simulation(s_args, python_version, venv_path):
    file_path = root / "src" / "simulation_app.py"
    if venv_path:
        subprocess.call([f"{str(venv_path)}/python{python_version}", str(file_path), *map(str, s_args)])
    else:
        subprocess.call([f"python{python_version}", str(file_path), *map(str, s_args)])


def start_api(a_args, python_version, path, qtd_agents):
    file_path = root / "src" / "socket_api_app.py"
    if path:
        subprocess.call([f"{str(path)}/python{python_version}", str(file_path), *map(str, a_args), str(qtd_agents)])
    else:
        subprocess.call([f"python{python_version}", str(file_path), *map(str, a_args), str(qtd_agents)])


def handle_enviroment(python_version, globally):
    if globally:
        return ''
    venv_path = root / 'venv'

    if os.name == 'nt':
        venv_path = venv_path / 'Scripts'
    else:
        venv_path = venv_path / 'bin'

    if not os.path.exists(venv_path):
        initialize_env(python_version)
    install_requirements(python_version, venv_path)

    return venv_path


def initialize_env(python_version):
    try:
        subprocess.call(['virtualenv', 'venv'])
    except FileNotFoundError:
        subprocess.call([f'pip{python_version}', 'install', 'virtualenv'])
        subprocess.call(['virtualenv', 'venv'])


def install_requirements(python_version, venv_path):
    if venv_path:
        subprocess.call([f"{str(venv_path)}/pip{python_version}", "install", "-r", "requirements.txt"])
    else:
        subprocess.call([f"pip{python_version}", "install", "-r", "requirements.txt"])


def handle_arguments():
    parser = create_parser()
    args = parser.parse_args()

    config_file_location = args.conf
    events = args.events

    if events == 'default':
        events_path = root / 'files' / default_events_path
    else:
        events_path = root / 'files' / events

    base_url = args.url
    simulation_port = args.sp
    api_port = args.ap
    pyversion = args.pyv
    step_time = args.step_t
    first_conn_time = args.first_t
    matches = args.matches

    return [config_file_location, events_path, base_url, simulation_port, api_port], \
           [base_url, api_port, simulation_port, step_time, first_conn_time, matches], \
           pyversion, args.g


def create_parser():
    parser = argparse.ArgumentParser(prog='Disaster Simulator')
    parser.add_argument('-conf', required=True, type=str)
    parser.add_argument('-events', required=False, type=str, default='default')
    parser.add_argument('-url', required=False, type=str, default='127.0.0.1')
    parser.add_argument('-sp', required=False, type=str, default='8910')
    parser.add_argument('-ap', required=False, type=str, default='12345')
    parser.add_argument('-pyv', required=False, type=str, default='')
    parser.add_argument('-g', required=False, type=bool, default=False)
    parser.add_argument('-step_t', required=False, type=int, default=1)
    parser.add_argument('-first_t', required=False, type=int, default=5)
    parser.add_argument('-matches', required=False, type=int, default=1)
    return parser


if __name__ == '__main__':
    simulation_args, api_args, pyv, globally = handle_arguments()
    path = handle_enviroment(pyv, globally)

    qt_agents = 0
    with open(simulation_args[0], 'r') as file:
        json_file = json.loads(file.read())
        for role in json_file['agents']:
            qt_agents += json_file['agents'][role]

    simulation = multiprocessing.Process(target=start_simulation, args=(simulation_args, pyv, path), daemon=True)
    api = multiprocessing.Process(target=start_api, args=(api_args, pyv, path, qt_agents), daemon=True)

    simulation.start()
    api.start()

    simulation.join()
    api.join()
