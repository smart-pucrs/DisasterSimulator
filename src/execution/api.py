"""This module is the entry point for all the calls that the simulation will receive, all the validations and controls
are done here. It represents the server of the simulation and also the step controller.

Note: any changes on the control functions must be done carefully."""

import os
import sys
import json
import logging
import time
import queue
import signal
import requests
import multiprocessing
from multiprocessing import Queue
from flask_socketio import SocketIO
from flask import Flask, request, jsonify
from communication.controllers.controller import Controller
from communication.helpers import json_formatter
from communication.helpers.logger import Logger

logging.basicConfig(format="[API] [%(levelname)s] %(message)s",level=logging.DEBUG)
logger = logging.getLogger(__name__)

base_url, api_port, simulation_port, monitor_port, step_time, first_step_time, method, log, social_assets_timeout, secret, agents_amount = sys.argv[1:]

app = Flask(__name__)
socket = SocketIO(app=app)
logging.getLogger('socketio').setLevel(logging.ERROR)
logging.getLogger('engineio').setLevel(logging.ERROR)

controller = Controller(agents_amount, first_step_time, secret)
every_agent_registered = Queue()
one_agent_registered_queue = Queue()
actions_queue = Queue()
request_queue = Queue()

# Events variables
initial_percepts_event = 'initial_percepts'
percepts_event = 'percepts'
end_event = 'end'
bye_event = 'bye'
error_event = 'error'

monitor_connected = False

@app.route('/sim_config', methods=['GET'])
def sim_config():
    """Return the bases information of the simulator.
    """
    global monitor_connected

    simulation_url = f'http://{base_url}:{simulation_port}'
    api_url = f'http://{base_url}:{api_port}'

    response = dict(
        simulation_url=simulation_url,
        api_url=api_url,
        max_agents=agents_amount,
        first_step_time=first_step_time,
        step_time=step_time,
        social_asset_timeout=social_assets_timeout
    )

    monitor_connected = True
    Logger.normal('Sending simulation config to GUI.')

    return jsonify(response)


@app.route('/start_connections', methods=['POST'])
def start_connections():
    """Starts the API as entry point, before calling this functions the API will only answer that the simulation
    is not online.

    It also starts processes that will handle the first step cycle. The first step cycle can be completed in some
    different ways:

    1 - All the agents connected at once: This is the expected condition for the simulation to start running, after all
    the agents connect to it, the steps engine will proceed.

    2 - Less than the total of agents connected and the time ended: It is not the perfect scenario, but is possible. If
    just one of five agents connects to the simulation it will wait for the time to end, if it ends, the steps engine
    will proceed with only that agent connected.

    3 - No agent connected and the time ended: This is the worst scenario possible for the time, if no agent is connected
    than the simulation will never start.

    4 - The user pressed any button: This is the scenario where the user has the full control of the start, it will only
    start the steps engine when the user allows it.

    Note: This endpoint must be called from the simulation, it is not recommended to the user to call it on his own."""

    Logger.normal('Start connections')

    try:
        valid, message = controller.do_internal_verification(request)
        
        if not valid:
            return jsonify(message=f'This endpoint can not be accessed. {message}')

        if message['back'] != 1:
            controller.set_started()

            if method == 'time':
                multiprocessing.Process(target=first_step_time_controller, args=(every_agent_registered,), daemon=True).start()

            else:
                multiprocessing.Process(target=first_step_button_controller, daemon=True).start()

        else:
            multiprocessing.Process(target=first_step_time_controller, args=(one_agent_registered_queue,), daemon=True).start()

        controller.start_timer()

        return jsonify('')

    except json.JSONDecodeError:
        return jsonify(message='This endpoint can not be accessed.')


def first_step_time_controller(ready_queue):
    """Waits for either all the agents connect or the time end.

    If all the agents connect, it will start the steps engine and run the simulation with them.
    If some of the agents does not connect it will call the start_connections endpoint and retry."""

    agents_connected = False

    try:
        if int(agents_amount) > 0:
            agents_connected = ready_queue.get(block=True, timeout=int(first_step_time))

        else:
            agents_connected = True

    except queue.Empty:
        pass

    if not agents_connected:
        requests.post(f'http://{base_url}:{api_port}/start_connections', json={'secret': secret, 'back': 1})

    else:
        requests.get(f'http://{base_url}:{api_port}/start_step_cycle', json={'secret': secret})

    os.kill(os.getpid(), signal.SIGTERM)


def first_step_button_controller():
    """Wait for the user to press any button, the recommended is 'Enter', but there are no restrictions."""

    sys.stdin = open(0)
    Logger.normal('When you are ready press "Enter"')
    sys.stdin.read(1)

    requests.get(f'http://{base_url}:{api_port}/start_step_cycle', json=secret)


@app.route('/start_step_cycle', methods=['GET'])
def start_step_cycle():
    """Start the steps engine and notify the agents that are connected to it that the simulation is starting.

    Note: When this endpoint is called, the agents or social assets can only send actions to the simulation.
    Note: This endpoint must be called from the simulation, it is not recommended to the user to call it on his own."""

    valid, message = controller.do_internal_verification(request)

    if not valid:
        return jsonify(message=f'This endpoint can not be accessed. {message}')

    controller.finish_connection_timer()

    sim_response = requests.post(f'http://{base_url}:{simulation_port}/start', json={'secret': secret}).json()

    notify_monitor(initial_percepts_event, sim_response)
    notify_monitor(percepts_event, sim_response)
    notify_actors(percepts_event, sim_response)

    multiprocessing.Process(target=step_controller, args=(actions_queue, 1), daemon=True).start()

    return jsonify('')


@app.route('/connect_agent', methods=['POST'])
def connect_agent():
    """Connect the agent.

    If the agent is successfully connected, the simulation will return its token, any errors, it will return the error
    message and the corresponding status."""

    response = {'status': 1, 'result': True, 'message': 'Error.'}
    connecting_agent = True

    if controller.processing_asset_request():
        Logger.normal('Try to connect a social asset.')
        status, message = controller.do_social_asset_connection(request)
        connecting_agent = False

    else:
        Logger.normal('Try to connect a agent.')
        status, message = controller.do_agent_connection(request)

    if status != 1:
        if connecting_agent:
            Logger.error(f'Error to connect the agent: {message}')
        else:
            Logger.error(f'Error to connect the social asset: {message}')

        response['status'] = status
        response['result'] = False
    else:
        if connecting_agent:
            Logger.normal('Agent connected.')
        else:
            Logger.normal('Social asset connected.')

    response['message'] = message

    return jsonify(response)


@socket.on('register_agent')
def register_agent(msg):
    """Connect the socket of the agent.

    If no errors found, the agent information is sent to the engine and it will create its own object of the agent.

    Note: The agent must be registered to connect the socket."""

    response = {'type': 'initial_percepts', 'status': 0, 'result': False, 'message': 'Error.'}
    registering_agent = True

    if controller.processing_asset_request():
        registering_agent = False
        Logger.normal('Try to register and connect the social asset socket.')
        status, message = controller.do_social_asset_registration(msg, request.sid)
    else:
        Logger.normal('Try to register and connect the agent socket.')
        status, message = controller.do_agent_registration(msg, request.sid)

    if status == 1:
        try:
            if not registering_agent:
                main_token = message[0]
                token = message[1]
                sim_response = requests.post(f'http://{base_url}:{simulation_port}/register_asset',
                                             json={'main_token': main_token, 'token': token, 'secret': secret}).json()

                if sim_response['status'] == 1:
                    Logger.normal('Social asset socket connected.')

                    response['status'] = 1
                    response['result'] = True
                    response['message'] = 'Social asset successfully connected'

                    if controller.check_requests():
                        request_queue.put(True)

                    response.update(sim_response)
                    send_initial_percepts(token, response)

                else:
                    Logger.error(f'Error to connect the social asset socket: {message}')

                    response['status'] = sim_response['status']
                    response['message'] = sim_response['message']
            else:
                sim_response = requests.post(f'http://{base_url}:{simulation_port}/register_agent',
                                             json={'token': message, 'secret': secret}).json()

                if sim_response['status'] == 1:
                    Logger.normal('Agent socket connected.')

                    response['status'] = 1
                    response['result'] = True
                    response['message'] = 'Agent successfully connected.'

                    response.update(sim_response)

                    if controller.agents_amount == len(controller.manager.agents_sockets_manager.get_tokens()):
                        every_agent_registered.put(True)

                    one_agent_registered_queue.put(True)

                    send_initial_percepts(message, response)

                else:
                    Logger.error(f'Error to connect the agent socket: {message}')

                    response['status'] = sim_response['status']
                    response['message'] = sim_response['message']

        except requests.exceptions.ConnectionError:
            response['status'] = 6
            response['message'] = 'Simulation is not online.'

    else:
        Logger.error(f'Unknown error: {message}')
        response['status'] = status
        response['message'] = message

    return jsonify(0)


@app.route('/finish_step', methods=['GET'])
def finish_step():
    """Finish each step of the simulation.

    Every time the simulation finished one step, all the actions sent are processes by the engine and
    the agents and social assets are notified if the simulation ended, their actions results or if the
    simulation restarted.
    Internal errors at the engine of the API will stop the system to prevent of running hundreds of steps
    to find that on step 12 the simulation had an error and all the next steps were not executed properly.

    Note: When the engine is processing the actions, the agents or social assets can not send any action.
    Note: This endpoint must be called from the simulation, it is not recommended to the user to call it on his own."""

    Logger.normal('Preparing the actions to send.')

    valid, message = controller.do_internal_verification(request)

    if not valid:
        return jsonify(message=f'This endpoint can not be accessed. {message}')

    try:
        controller.set_processing_actions()
        tokens_actions_list = [*controller.manager.get_actions('agent'), *controller.manager.get_actions('social_asset')]

        logger.info('sending actions to the simulation engine')
        sim_response = requests.post(f'http://{base_url}:{simulation_port}/do_actions', json={'actions': tokens_actions_list, 'secret': secret}).json()
        logger.info('receiving actions results')
        controller.manager.clear_workers()

        if sim_response['status'] == 0:
            logger.critical('An internal error occurred. Shutting down...')
            notify_monitor(error_event, {'message': 'An internal error occurred. Shutting down...'})

            requests.get(f'http://{base_url}:{simulation_port}/terminate', json={'secret': secret, Logger.TAG_NORMAL: True})
            multiprocessing.Process(target=auto_destruction, daemon=True).start()

        if sim_response['message'] == 'Simulation finished.':
            Logger.normal('End of the simulation, preparer to restart.')

            sim_response = requests.put(f'http://{base_url}:{simulation_port}/restart', json={'secret': secret}).json()

            notify_monitor(end_event, sim_response['report'])
            notify_actors(end_event, sim_response['report'])

            if sim_response['status'] == 0:
                Logger.normal('No more map to run, finishing the simulation...')

                sim_response = requests.get(f'http://{base_url}:{simulation_port}/terminate', json={'secret': secret, 'api': True}).json()

                notify_monitor(bye_event, sim_response)
                notify_actors(bye_event, sim_response)

                multiprocessing.Process(target=auto_destruction, daemon=True).start()

            else:
                Logger.normal('Restart the simulation.')

                controller.clear_social_assets(sim_response['assets_tokens'])
                controller.new_match()

                notify_monitor(initial_percepts_event, sim_response['initial_percepts'])
                notify_actors(initial_percepts_event, sim_response['initial_percepts'])
                notify_monitor(percepts_event, sim_response['percepts'])
                notify_actors(percepts_event, sim_response['percepts'])

                controller.set_processing_actions()
                multiprocessing.Process(target=step_controller, args=(actions_queue, 1), daemon=True).start()

        else:
            controller.set_processing_actions()
            notify_monitor(percepts_event, sim_response)

            if sim_response['status'] == 2:
                Logger.normal('Open connections for the social assets.')

                controller.start_social_asset_request(sim_response)
                multiprocessing.Process(target=step_controller, args=(request_queue, 2), daemon=True).start()

            else:
                notify_actors(percepts_event, sim_response)
                Logger.normal('Wait all the agent send yours actions.')

                multiprocessing.Process(target=step_controller, args=(actions_queue, 1), daemon=True).start()

    except requests.exceptions.ConnectionError:
        logger.critical('Error to process the agents actions.',exc_info=True)

        pass

    return jsonify(0)


@app.route('/handle_response', methods=['GET'])
def handle_response():
    Logger.normal('Handle the agent response after try to connect the social asset.')

    tokens = controller.get_social_assets_tokens()

    sim_response = requests.post(f'http://{base_url}:{simulation_port}/finish_social_asset_connections',
                                 json={'tokens': tokens, 'secret': secret}).json()

    response = controller.format_actions_result(sim_response)
    notify_actors(percepts_event, response)
    controller.finish_assets_connections()

    multiprocessing.Process(target=step_controller, args=(actions_queue, 1), daemon=True).start()

    return jsonify(0)


def step_controller(ready_queue, status):
    """Wait for all the agents to send their actions or the time to end either one will cause the method to call
    finish_step."""

    if status == 2:
        try:
            ready_queue.get(block=True, timeout=int(social_assets_timeout))

        except queue.Empty:
            pass
    else:
        try:
            if int(agents_amount) > 0:
                ready_queue.get(block=True, timeout=int(step_time))

        except queue.Empty:
            pass

    try:
        if status == 2:
            requests.get(f'http://{base_url}:{api_port}/handle_response', json={'secret': secret})
        else:
            requests.get(f'http://{base_url}:{api_port}/finish_step', json={'secret': secret})

    except requests.exceptions.ConnectionError:
        pass

    os.kill(os.getpid(), signal.SIGTERM)


@socket.on('send_action')
def send_action_temp(msg):
    """Receive all the actions from the agents or social assets.

        Note: The actions are stored and only used when the step is finished and the simulation process it."""

    response = {'status': 1, 'result': True, 'message': 'Error.'}
    status, message = controller.do_action(msg)

    if status != 1:
        Logger.error('Error to storage the action received.')

        response['status'] = status
        response['result'] = False

    else:
        every_socket = controller.manager.get_all('socket')
        tokens_connected_size = len([*every_socket[0], *every_socket[1]])
        agent_workers_size = len(controller.manager.get_workers('agent'))
        social_asset_workers_size = len(controller.manager.get_workers('social_asset'))
        workers = agent_workers_size + social_asset_workers_size

        Logger.normal(f'Action received: {workers} of {tokens_connected_size}.')

        if tokens_connected_size == workers:
            Logger.normal('All actions received.')

            actions_queue.put(True)

    response['message'] = message


@socket.on('disconnect_registered_agent')
def disconnect_registered_agent(msg):
    """Disconnect the agent.

    The agent is removed from the API and will not be able to connect of send actions to it."""

    response = {'status': 0, 'result': False, 'message': 'Error.'}

    status, message = controller.do_agent_socket_disconnection(msg)

    if status == 1:
        try:
            sim_response = requests.put(f'http://{base_url}:{simulation_port}/delete_agent',
                                        json={'token': message, 'secret': secret}).json()

            if sim_response['status'] == 1:
                response['status'] = 1
                response['result'] = True
                response['message'] = 'Agent successfully disconnected.'

            else:
                response['message'] = sim_response['message']

        except json.decoder.JSONDecodeError:
            response['message'] = 'An internal error occurred at the simulation.'

        except requests.exceptions.ConnectionError:
            response['message'] = 'Simulation is not online.'

    Logger.normal(f'Disconnect a agent, message: {message}')

    return json.dumps(response, sort_keys=False)


@socket.on('disconnect_registered_asset')
def disconnect_registered_asset(msg):
    """Disconnect the social asset.

    The social asset is removed from the API and will not be able to connect of send actions to it."""

    response = {'status': 0, 'result': False, 'message': 'Error.'}

    status, message = controller.do_social_asset_socket_disconnection(msg)

    if status == 1:
        try:
            sim_response = requests.put(f'http://{base_url}:{simulation_port}/delete_asset',
                                        json={'token': message, 'secret': secret}).json()

            if sim_response['status'] == 1:
                response['status'] = 1
                response['result'] = True
                response['message'] = 'Social asset successfully disconnected.'

            else:
                response['message'] = sim_response['message']

        except json.decoder.JSONDecodeError:
            response['message'] = 'An internal error occurred at the simulation.'

        except requests.exceptions.ConnectionError:
            response['message'] = 'Simulation is not online.'

    return json.dumps(response, sort_keys=False)


def send_initial_percepts(token, info):
    """Send the initial percepts for the agent informed.

    The message contain the agent and map percepts."""

    room = controller.manager.get(token, 'socket')
    response = json_formatter.initial_percepts_format(info, token)
    socket.emit(initial_percepts_event, response, room=room)


def notify_monitor(event, response):
    """ Update data into the monitor."""
    # TODO: for now does nothing
    global monitor_connected
    if not monitor_connected: 
        return 
    Logger.normal('Update monitor.')

    url = f'http://{base_url}:{monitor_port}/simulator'

    if event == initial_percepts_event:
        # logger.debug(response)
        info = json_formatter.initial_percepts_monitor_format(response)
        match = controller.get_current_match()
        url = f'{url}/match/{match}/info/map'

    elif event == percepts_event:
        info = json_formatter.percepts_monitor_format(response)
        match = controller.get_current_match()
        url = f'{url}/match/{match}/step'

    elif event == end_event:
        info = json_formatter.end_monitor_format(response)
        match = controller.get_current_match()
        url = f'{url}/match/{match}/info/report'

    elif event == bye_event:
        info = json_formatter.end_monitor_format(response)
        url = f'{url}/info/report'

    else:
        Logger.error('Event type in "notify monitor" not found.')
        return

    monitor_response = requests.post(url, json=info)

    if not monitor_response:
        Logger.error('Error sending data to monitor.')


def notify_actors(event, response):
    """Notify the agents and social assets through sockets.

    Each agent and each social asset has its own message related.

    Note: If an unknown event name is given, the simulation will stop because it was almost certainly caused by
    internal errors."""

    Logger.normal('Notifying the agents.')

    tokens = [*controller.manager.agents_sockets_manager.get_tokens(), *controller.manager.assets_sockets_manager.get_tokens()]
    room_response_list = []

    for token in tokens:
        if event == initial_percepts_event:
            info = json_formatter.initial_percepts_format(response, token)

        elif event == percepts_event:
            info = json_formatter.percepts_format(response, token)

        elif event == end_event:
            info = json_formatter.end_format(response, token)

        elif event == bye_event:
            info = json_formatter.bye_format(response, token)

        else:
            Logger.error('Wrong event name. Possible internal errors.')
            info = json_formatter.event_error_format('Error in API.')

        room = controller.manager.get(token, 'socket')
        room_response_list.append((room, json.dumps(info)))

    for room, agent_response in room_response_list:
        socket.emit(event, agent_response, room=room)
        

@app.route('/call_service', methods=['GET'])
def calculate_route():
    """Send a request for the simulator to calculate a route between the coord given."""

    response = {'status': 0, 'result': False, 'message': ''}

    if not controller.simulation_started():
        response['message'] = 'The simulator has not started yet.'

    else:
        status, message = controller.check_service_request(request)

        if status == 1:
            # Can be add more types of services
            sim_response = requests.get(f'http://{base_url}:{simulation_port}/calculate_route',
                                        json={'parameters': request.get_json(force=True)['parameters'], 'secret': secret}).json()

            if sim_response['status'] == 1:
                response['status'] = 1
                response['result'] = True
                response['response'] = sim_response['response']
            else:
                response['message'] = sim_response['message']
        else:
            response['message'] = message

    return jsonify(response)


@app.route('/terminate', methods=['GET'])
def terminate():
    """Terminate the process that runs the API.

    Note: This endpoint must be called from the simulation, it is not recommended to the user to call it on his own."""

    valid, message = controller.do_internal_verification(request)

    if not valid:
        return jsonify(message='This endpoint can not be accessed.')

    if 'back' not in message:
        return jsonify(message='This endpoint can not be accessed.')

    if message['back'] == 0:
        multiprocessing.Process(target=auto_destruction, daemon=True).start()
    else:
        socket.stop()
        os.kill(os.getpid(), signal.SIGTERM)

    return jsonify('')


def auto_destruction():
    """Wait one second and then call the terminate endpoint."""

    time.sleep(1)
    try:
        requests.get(f'http://{base_url}:{api_port}/terminate', json={'secret': secret, 'back': 1})
    except requests.exceptions.ConnectionError:
        pass

    os.kill(os.getpid(), signal.SIGTERM)


if __name__ == '__main__':
    app.config['SECRET_KEY'] = secret
    app.config['JSON_SORT_KEYS'] = False
    Logger.normal(f'API: Serving on http://{base_url}:{api_port}')
    socket.run(app=app, host=base_url, port=api_port)
