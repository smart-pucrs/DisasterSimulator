import requests
import json
import socketio


asset = {'name': 'pass_action_test'}
wait = True
responses = []


socket = socketio.Client()
token = None
counter = 0
max_iter = 4


def connect_asset():
    global token
    response = requests.post('http://127.0.0.1:12345/connect_asset', json=json.dumps(asset)).json()
    token = response['message']
    requests.post('http://127.0.0.1:12345/register_asset', json=json.dumps({'token': token}))
    socket.emit('connect_registered_asset', data=json.dumps({'token': token}))


@socket.on('simulation_started')
def simulation_started(msg):
    requests.post('http://127.0.0.1:12345/send_action', json=json.dumps({'token': token, 'action': 'pass', 'parameters': []}))


@socket.on('action_results')
def action_result(msg):
    global counter

    if counter == max_iter:
        socket.emit('disconnect_registered_asset', data=json.dumps({'token': token}), callback=quit_program)
    else:
        requests.post('http://127.0.0.1:12345/send_action', json=json.dumps({'token': token, 'action': 'pass', 'parameters': []}))
        counter += 1


@socket.on('simulation_ended')
def simulation_ended(*args):
    global wait
    wait = False


def quit_program(*args):
    global wait
    wait = False


def test_cycle():
    socket.connect('http://127.0.0.1:12345')
    connect_asset()
    while wait:
        pass

    socket.disconnect()
    assert all(responses)


if __name__ == '__main__':
    try:
        test_cycle()
        print(True)
    except AssertionError:
        print(False)
