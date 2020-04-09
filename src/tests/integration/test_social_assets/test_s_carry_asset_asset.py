import json
import requests
import socketio


asset = {'name': 'carry_asset'}
carried_asset = {'name': 'carried_asset'}

waits = []
responses = []


carry_socket = socketio.Client()
carried_socket = socketio.Client()
token = None
carried_token = None


def connect_actors():
    global token, carried_token

    response = requests.post('http://127.0.0.1:12345/connect_asset', json=json.dumps(asset)).json()
    token = response['message']
    requests.post('http://127.0.0.1:12345/register_asset', json=json.dumps({'token': token}))
    carry_socket.emit('connect_registered_asset', data=json.dumps({'token': token}))

    carried_response = requests.post('http://127.0.0.1:12345/connect_asset', json=json.dumps(carried_asset)).json()
    carried_token = carried_response['message']
    requests.post('http://127.0.0.1:12345/register_asset', json=json.dumps({'token': carried_token}))
    carried_socket.emit('connect_registered_asset', data=json.dumps({'token': carried_token}))


@carry_socket.on('simulation_started')
def carry_simulation_started(msg):
    requests.post('http://127.0.0.1:12345/send_action', json=json.dumps({'token': token, 'action': 'carry', 'parameters': [carried_token]}))


@carried_socket.on('simulation_started')
def carried_simulation_started(msg):
    requests.post('http://127.0.0.1:12345/send_action', json=json.dumps({'token': carried_token, 'action': 'getCarried', 'parameters': [token]}))


@carry_socket.on('action_results')
def carry_action_results(msg):
    msg = json.loads(msg)
    responses.append(msg['social_asset']['last_action_result'])
    carry_socket.emit('disconnect_registered_asset', data=json.dumps({'token': token}), callback=quit_program)


@carried_socket.on('action_results')
def carried_action_results(msg):
    msg = json.loads(msg)
    responses.append(msg['social_asset']['last_action_result'])
    carried_socket.emit('disconnect_registered_asset', data=json.dumps({'token': carried_token}), callback=quit_program)


def quit_program(*args):
    waits.append(True)


def test_cycle():
    carry_socket.connect('http://127.0.0.1:12345')
    carried_socket.connect('http://127.0.0.1:12345')
    connect_actors()
    while len(waits) < 2:
        pass

    carry_socket.disconnect()
    carried_socket.disconnect()

    assert all(responses)


if __name__ == '__main__':
    try:
        test_cycle()
        print(True)
    except AssertionError:
        print(False)
