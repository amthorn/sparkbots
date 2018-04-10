import flask
import ciscosparkapi
import json

from queuebot.decorators import with_request
from unittest import mock
from contextlib import contextmanager
from tests.scaffolding import CAT_FACT, DAD_JOKE, SUPPORTED_ADMIN_COMMANDS, SUPPORTED_COMMANDS
from app import VERSION, RELEASED, AUTHOR, EMAIL
from freezegun import freeze_time
from attrdict import AttrDict

def test_empty_data():
    with mock.patch("flask.request") as mock_api:
        flask.request.json={}
        with mock.patch("ciscosparkapi.CiscoSparkAPI") as mock_api:
            from endpoints import queue
            queue()


@with_request(
    data=dict(mentionedPeople={1})
)
def test_early_exception():
    from endpoints import CiscoSparkAPI, queue
    og = CiscoSparkAPI.return_value
    CiscoSparkAPI.return_value = None
    try:
        queue()
    except Exception as e:
        pass
    else:
        assert False, "Exception not raised as expected"
    CiscoSparkAPI.return_value = og


@mock.patch('endpoints.PRODUCTION')
@with_request(
    data=dict(mentionedPeople={1})
)
def test_early_exception_production(mock_production):
    from endpoints import CiscoSparkAPI, queue
    og = CiscoSparkAPI.return_value
    CiscoSparkAPI.return_value = None
    result = queue()
    assert result == '500 Internal Server Error'
    CiscoSparkAPI.return_value = og


@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot list",
      "personId": "non-admin",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    }
)
def test_unregistered():
    from endpoints import queue, CiscoSparkAPI
    queue()
    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='QueueBot is not registered to a project! Ask an admin to register this bot',
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args
    commands = args[0]
    assert commands[-1]['sparkId'] == 'message-id' and commands[-1]['command'] == 'list'


@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot status",
      "personId": "non-admin",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    project={'BLAH': 'UNIT_TEST'}
)
def test_queue_status_ok():
    from endpoints import queue, CiscoSparkAPI
    queue()
    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='STATUS: OK',
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args
    commands = args[0]
    assert commands[-1]['sparkId'] == 'message-id' and commands[-1]['command'] == 'status'


@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot how long",
      "personId": "test_how_long_nonadmin",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    project={'BLAH': 'UNIT_TEST'},
    queue=[]
)
def test_how_long_nonadmin_empty_queue():
    from endpoints import queue, CiscoSparkAPI
    queue()
    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='Given that there are 0 people in the queue. '
                        'Estimated wait time from the back of the queue is:\n\n0:00:00',
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args
    commands = args[0]
    assert commands[-1]['sparkId'] == 'message-id' and commands[-1]['command'] == 'how long'

@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot how long",
      "personId": "test_how_long_nonadmin_nonempty_queue",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    project={'BLAH': 'UNIT_TEST'},
    queue=[{
        "atHeadTime": "1980-01-01 11:30:00.000000",
        "displayName": "Blah",
        "personId": "test_how_long_nonadmin_nonempty_queue",
        "timeEnqueued": "1980-01-01 11:00:00.000000"
    }],
    people=[{
        "sparkId": "test_how_long_nonadmin_nonempty_queue",
        "displayName": "Ava Thorn",
        "project": "UNIT_TEST",
        "totalTimeInQueue": 1000,
        "totalTimeAtHead": 900,
        "currentlyInQueue": False,
        "admin": False,
        "commands": 5,
        "number_of_times_in_queue": 1,
        "added_to_queue": [
            "1980-01-01 11:00:00.000000"
        ],
        "removed_from_queue": []
    }]
)
def test_how_long_nonadmin_nonempty_queue():
    from endpoints import queue, CiscoSparkAPI
    queue()
    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='Given that there are 1 people in the queue. '
                        'Estimated wait time from the back of the queue is:\n\n0:45:00',
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args
    commands = args[0]
    assert commands[-1]['sparkId'] == 'message-id' and commands[-1]['command'] == 'how long'


@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot help",
      "personId": "non-admin",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    project={'BLAH': 'UNIT_TEST'}
)
def test_queue_help_unregistered():
    from endpoints import queue, CiscoSparkAPI
    from queuebot import Bot
    import endpoints
    queue()

    help_string = \
        "This bot is to be used to manage a queue for a given team. " \
        "It can be used to get statistical information as well as manage an individual queue.\n" \
        "\n" \
        "This QueueBot is registered to '" + str('UNIT_TEST') + "'\n" \
                                                                 "\n" \
                                                                 "Available commands are:\n- " \
        + '- '.join([(i + '\n') for i in SUPPORTED_COMMANDS]) + \
        "\n" \
        "For admins, use 'show admin commands' to see a list of admin commands"
    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown=help_string,
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args
    commands = args[0]
    assert commands[-1]['sparkId'] == 'message-id' and commands[-1]['command'] == 'help'


@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot cat fact",
      "personId": "non-admin",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    project={'BLAH': 'UNIT_TEST'}
)
def test_cat_fact():
    from endpoints import queue, CiscoSparkAPI
    with mock.patch('requests.get') as mock_requests:
        foo = mock.MagicMock()
        foo.json.return_value = CAT_FACT

        mock_requests.return_value = foo
        queue()
    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown=CAT_FACT['fact'],
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args
    commands = args[0]
    assert commands[-1]['sparkId'] == 'message-id' and commands[-1]['command'] == 'cat fact'


@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot pun",
      "personId": "non-admin",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    project={'BLAH': 'UNIT_TEST'}
)
def test_dad_joke():
    from endpoints import queue, CiscoSparkAPI
    with mock.patch('requests.get') as mock_requests:
        foo = mock.MagicMock()
        foo.json.return_value = DAD_JOKE

        mock_requests.return_value = foo
        queue()
    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown=DAD_JOKE['joke'],
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args
    commands = args[0]
    assert commands[-1]['sparkId'] == 'message-id' and commands[-1]['command'] == 'pun'


@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show admin commands",
      "personId": "non-admin",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    project={'BLAH': 'UNIT_TEST'}
)
def test_admin_command_by_nonadmin():
    from endpoints import queue, CiscoSparkAPI
    queue()
    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='You are not registered as an admin.',
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args
    commands = args[0]
    assert commands[-1]['sparkId'] == 'message-id' and commands[-1]['command'] == 'show admin commands'


@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show admin commands",
      "personId": "admin",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    project={'BLAH': 'UNIT_TEST'},
    admins=['admin']
)
def test_admin_command_by_admin():
    from endpoints import queue, CiscoSparkAPI
    queue()

    string = 'Available admin commands are:\n- ' + ('- '.join([(i + '\n') for i in SUPPORTED_ADMIN_COMMANDS]))

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown=string,
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args
    commands = args[0]
    assert commands[-1]['sparkId'] == 'message-id' and commands[-1]['command'] == 'show admin commands'


@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot list",
      "personId": "non-admin",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    project={'BLAH': 'UNIT_TEST'}
)
def test_list_empty():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='Current queue is:\n\nThere is no one in the queue',
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args
    commands = args[0]
    assert commands[-1]['sparkId'] == 'message-id' and commands[-1]['command'] == 'list'


@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot about",
      "personId": "non-admin",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    project={'BLAH': 'UNIT_TEST'}
)
def test_list_empty():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown="This bot is to be used to manage a queue for a given team. "
                        "It can be used to get statistical information as well as manage an individual queue.\n\n"
                        "This QueueBot is registered to 'UNIT_TEST'\n\n"
                        "Version: **" + str(VERSION)  + "**\n\n"
                        "Released: " + str(RELEASED) + "\n\n"
                        "Author: " + str(AUTHOR) + " (" + str(EMAIL) + ")",
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args
    commands = args[0]
    assert commands[-1]['sparkId'] == 'message-id' and commands[-1]['command'] == 'about'


@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot list",
      "personId": "non-admin",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    project={'BLAH': 'UNIT_TEST'},
    queue=[{
        "personId": "fooid",
        "timeEnqueued": "2018-04-06 12:34:45.678901",
        "displayName": "Unit Test Display Name",
        "atHeadTime": "2018-04-06 12:31:26.851938"
    }]
)
def test_list_one_member():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='Current queue is:\n\n1. Unit Test Display Name (12:34:45 PM on Fri, Apr 06)\n',
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args
    commands = args[0]
    assert commands[-1]['sparkId'] == 'message-id' and commands[-1]['command'] == 'list'


@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot list",
      "personId": "non-admin",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    project={'BLAH': 'UNIT_TEST'},
    queue=[{
        "personId": "fooid",
        "timeEnqueued": "2018-04-06 12:34:45.678901",
        "displayName": "Unit Test Display Name",
        "atHeadTime": "2018-04-06 12:31:26.851938"
    },{
        "personId": "fooid2",
        "timeEnqueued": "2018-04-07 12:34:45.678901",
        "displayName": "Unit Test Display Name 2",
        "atHeadTime": None
    }]
)
def test_list_two_members():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='Current queue is:\n\n'
                        '1. Unit Test Display Name (12:34:45 PM on Fri, Apr 06)\n'
                        '2. Unit Test Display Name 2 (12:34:45 PM on Sat, Apr 07)\n',
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args
    commands = args[0]
    assert commands[-1]['sparkId'] == 'message-id' and commands[-1]['command'] == 'list'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot add me",
      "personId": "test_add_me_empty_queue",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    project={'BLAH': 'UNIT_TEST'},
    queue=[],
    global_stats={'historicalData': {}}
)
def test_add_me_empty_queue():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 2, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args_list[0] == \
        mock.call(markdown="Adding 'Unit Test Display Name'", roomId='BLAH')
    assert CiscoSparkAPI().messages.create.call_args_list[1] == \
           mock.call(
               markdown='Current queue is:\n\n1. Unit Test Display Name (12:00:00 PM on Tue, Jan 01)\n',
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args_list[0]
    assert 'test_add_me_empty_queue' in [i['sparkId'] for i in args[0]]

    args, kwargs = json.dump.call_args_list[4]
    assert 'test_add_me_empty_queue' in [i['personId'] for i in args[0]]

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'add me'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot add me",
      "personId": "test_add_me_one_in_queue",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    project={'BLAH': 'UNIT_TEST'},
    queue=[{
        "personId": "first-id",
        "timeEnqueued": "2018-04-06 12:31:22.458645",
        "displayName": "Unit Test Display Name 1",
        "atHeadTime": "2018-04-06 12:31:26.851938"
    }],
    global_stats={'historicalData': {}}
)
def test_add_me_one_in_queue():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 2, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args_list[0] == \
        mock.call(markdown="Adding 'Unit Test Display Name'", roomId='BLAH')
    assert CiscoSparkAPI().messages.create.call_args_list[1] == \
           mock.call(
               markdown='Current queue is:\n\n1. Unit Test Display Name 1 (12:31:22 PM on Fri, Apr 06)\n'
                        '2. Unit Test Display Name (12:00:00 PM on Tue, Jan 01)\n',
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args_list[0]
    assert 'test_add_me_one_in_queue' in [i['sparkId'] for i in args[0]]

    args, kwargs = json.dump.call_args_list[4]
    assert len(args[0]) == 2
    assert 'test_add_me_one_in_queue' == args[0][-1]['personId']

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'add me'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot remove me",
      "personId": "test_remove_me_one_in_queue",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    project={'BLAH': 'UNIT_TEST'},
    queue=[{
        "personId": "test_remove_me_one_in_queue",
        "timeEnqueued": "2018-04-06 12:31:22.458645",
        "displayName": "Unit Test Display Name",
        "atHeadTime": "2018-04-06 12:31:26.851938"
    }],
    global_stats={'historicalData': {}}
)
def test_remove_me_one_in_queue():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 2, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args_list[0] == \
        mock.call(markdown="Removing 'Unit Test Display Name'", roomId='BLAH')
    assert CiscoSparkAPI().messages.create.call_args_list[1] == \
           mock.call(
               markdown='Current queue is:\n\nThere is no one in the queue',
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args_list[0]
    assert 'test_remove_me_one_in_queue' in [i['sparkId'] for i in args[0]]

    args, kwargs = json.dump.call_args_list[4]
    assert len(args[0]) == 0

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'remove me'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot remove me",
      "personId": "test_remove_me_one_in_queue",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    project={'BLAH': 'UNIT_TEST'},
    queue=[{
        "personId": "test_remove_me_one_in_queue",
        "timeEnqueued": "2018-04-06 12:31:22.458645",
        "displayName": "Unit Test Display Name",
        "atHeadTime": "2018-04-06 12:31:26.851938"
    }, {
        "personId": "test_remove_me_one_in_queue2",
        "timeEnqueued": "2018-04-06 12:31:22.458645",
        "displayName": "Unit Test Display Name",
        "atHeadTime": None
    }],
    global_stats={'historicalData': {}}
)
def test_remove_me_two_in_queue_me_at_head():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 2, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args_list[0] == \
        mock.call(markdown="Removing 'Unit Test Display Name'", roomId='BLAH')
    assert CiscoSparkAPI().messages.create.call_args_list[1] == \
           mock.call(
               markdown='Current queue is:\n\n1. Unit Test Display Name (12:31:22 PM on Fri, Apr 06)\n',
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args_list[0]
    assert 'test_remove_me_one_in_queue' in [i['sparkId'] for i in args[0]]

    args, kwargs = json.dump.call_args_list[3]
    assert len(args[0]) == 1

    args, kwargs = json.dump.call_args_list[1]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'remove me'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot remove me",
      "personId": "test_remove_me_one_in_queue_but_not_caller",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    project={'BLAH': 'UNIT_TEST'},
    queue=[{
        "personId": "foo",
        "timeEnqueued": "2018-04-06 12:31:22.458645",
        "displayName": "Unit Test Display Name",
        "atHeadTime": "2018-04-06 12:31:26.851938"
    }],
    global_stats={'historicalData': {}}
)
def test_remove_me_one_in_queue_but_not_caller():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 2, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args_list[0] == \
        mock.call(markdown="Removing 'Unit Test Display Name'", roomId='BLAH')

    assert CiscoSparkAPI().messages.create.call_args_list[1] == \
           mock.call(
               markdown="ERROR: 'Unit Test Display Name' was not found in the queue",
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args_list[0]
    assert 'test_remove_me_one_in_queue_but_not_caller' in [i['sparkId'] for i in args[0]]

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'remove me'


@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show admins",
      "personId": "test_show_admins",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    project={'BLAH': 'UNIT_TEST'},
    queue=[{
        "personId": "foo",
        "timeEnqueued": "2018-04-06 12:31:22.458645",
        "displayName": "Unit Test Display Name",
        "atHeadTime": "2018-04-06 12:31:26.851938"
    }],
    global_stats={'historicalData': {}},
    admins=['test_show_admins']
)
def test_show_admins():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"

    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown="Admins for 'UNIT_TEST' are:\n- Unit Test Display Name\n- Unit Test Display Name\n",
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args_list[0]
    assert 'test_show_admins' in [i['sparkId'] for i in args[0]]

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show admins'


@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot register bot to project lalala",
      "personId": "test_register_bot_by_admin",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_register_bot_by_admin']
)
def test_register_bot_by_admin():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown="Registered bot to project 'LALALA'",
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args_list[3]
    assert {'BLAH': 'LALALA'} == args[0]

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'register bot to project lalala'


@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot register bot to project should_not_work",
      "personId": "test_register_bot_by_nonadmin",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}}
)
def test_register_bot_by_nonadmin():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown="You are not registered as an admin.",
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and \
           args[0][-1]['command'] == 'register bot to project should_not_work'


@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot get all stats",
      "personId": "test_get_all_stats",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_get_all_stats'],
    people=[]
)
def test_get_all_stats():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown="```\n        PERSON         | AVERAGE TIME IN QUEUE | "
                        "AVERAGE TIME AT QUEUE HEAD | COMMANDS ISSUED | NUMBER "
                        "OF TIMES IN QUEUE | TOTAL TIME IN QUEUE | TOTAL TIME AT "
                        "QUEUE HEAD\nUnit Test Display Name |       0 seconds       "
                        "|         0 seconds          |        1        "
                        "|            0             |      0 seconds      |        "
                        "0 seconds        \n",
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and \
           args[0][-1]['command'] == 'get all stats'


@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show registration",
      "personId": "test_show_registration",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_show_registration'],
    project={'BLAH': 'UNIT_TEST'}
)
def test_show_registration():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown="QueueBot registration: UNIT_TEST",
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show registration'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show last 10 commands",
      "personId": "test_show_last_10_commands",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_show_last_10_commands'],
    project={'BLAH': 'UNIT_TEST'},
    commands=[{
        "sparkId": "unit_test1",
        "personId": "unit_test1",
        "displayName": "Ava Thorn",
        "roomId": "BLAH",
        "command": "add me",
        "timeIssued": "2018-04-09 13:41:22.418673"
    }]
)
def test_show_last_10_commands_1_command():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown="Last 10 commands are:\n"
                        "1. show last 10 commands (Unit Test Display Name executed at 12:00:00 PM on Tue, Jan 01)\n"
                        "2. add me (Ava Thorn executed at 01:41:22 PM on Mon, Apr 09)\n",
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show last 10 commands'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show last 10 commands",
      "personId": "test_show_last_10_commands_15_command",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_show_last_10_commands_15_command'],
    project={'BLAH': 'UNIT_TEST'},
    commands=[{
        "sparkId": "unit_test1",
        "personId": "unit_test1",
        "displayName": "Ava Thorn",
        "roomId": "BLAH",
        "command": "add me",
        "timeIssued": "2018-04-09 13:41:22.418673"
    }] * 15
)
def test_show_last_10_commands_15_command():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown="Last 10 commands are:\n"
                        "1. show last 10 commands (Unit Test Display Name executed at 12:00:00 PM on Tue, Jan 01)\n"
                        "2. add me (Ava Thorn executed at 01:41:22 PM on Mon, Apr 09)\n"
                        "3. add me (Ava Thorn executed at 01:41:22 PM on Mon, Apr 09)\n"
                        "4. add me (Ava Thorn executed at 01:41:22 PM on Mon, Apr 09)\n"
                        "5. add me (Ava Thorn executed at 01:41:22 PM on Mon, Apr 09)\n"
                        "6. add me (Ava Thorn executed at 01:41:22 PM on Mon, Apr 09)\n"
                        "7. add me (Ava Thorn executed at 01:41:22 PM on Mon, Apr 09)\n"
                        "8. add me (Ava Thorn executed at 01:41:22 PM on Mon, Apr 09)\n"
                        "9. add me (Ava Thorn executed at 01:41:22 PM on Mon, Apr 09)\n"
                        "10. add me (Ava Thorn executed at 01:41:22 PM on Mon, Apr 09)\n",
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show last 10 commands'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot add person UNIT_TEST_PERSON",
      "personId": "test_add_person",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id",
        "unit_test_person"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_add_person'],
    project={'BLAH': 'UNIT_TEST'},
    queue=[],
    mock_people={'unit_test_person': AttrDict({
        'displayName': 'Blah',
        'lastName': 'Blah Name',
        'emails': ['Blah@blah.blah'],
        'avatar': 'blah avatar'
    })}
)
def test_add_person():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 2, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args_list[0] == \
           mock.call(
               markdown="Adding 'Blah'",
               roomId='BLAH'
           ), "Sent message not correct"
    assert CiscoSparkAPI().messages.create.call_args_list[1] == \
           mock.call(
               markdown="Current queue is:\n\n1. Blah (12:00:00 PM on Tue, Jan 01)\n",
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args_list[5]
    assert [{
               'personId': 'unit_test_person',
               'timeEnqueued': '1980-01-01 12:00:00',
               'displayName': 'Blah',
               'atHeadTime': '1980-01-01 12:00:00'
           }] == args[0]

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'add person UNIT_TEST_PERSON'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot add admin Unit Test Person",
      "personId": "test_add_admin",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id",
        "unit_test_person"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_add_admin'],
    project={'BLAH': 'UNIT_TEST'},
    queue=[],
    mock_people={'unit_test_person': AttrDict({
        'displayName': 'New Admin',
        'lastName': 'Blah Name',
        'emails': ['Blah@blah.blah'],
        'avatar': 'blah avatar',
        'id': 'unit_test_person'
    })}
)
def test_add_admin():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 2, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args_list[0] == \
           mock.call(
               markdown="Added 'New Admin' as an admin.",
               roomId='BLAH'
           ), "Sent message not correct"
    assert CiscoSparkAPI().messages.create.call_args_list[1] == \
           mock.call(
               markdown="Admins for 'UNIT_TEST' are:\n"
                        "- Unit Test Display Name\n"
                        "- New Admin\n"
                        "- Unit Test Display Name\n",
               roomId='BLAH'
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[4]
    assert ['test_add_admin', 'unit_test_person'] == args[0]

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'add admin Unit Test Person'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot add admin Unit Test Person",
      "personId": "test_add_admin_already_admin",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id",
        "unit_test_person"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_add_admin_already_admin', 'unit_test_person'],
    project={'BLAH': 'UNIT_TEST'},
    queue=[],
    mock_people={'unit_test_person': AttrDict({
        'displayName': 'New Admin',
        'lastName': 'Blah Name',
        'emails': ['Blah@blah.blah'],
        'avatar': 'blah avatar',
        'id': 'unit_test_person'
    })}
)
def test_add_admin_already_admin():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown="'New Admin' is already an admin on this project",
               roomId='BLAH'
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'add admin Unit Test Person'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot add admin Unit Test Person",
      "personId": "test_add_admin",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id",
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_add_admin'],
    project={'BLAH': 'UNIT_TEST'},
    queue=[],
    mock_people={'unit_test_person': AttrDict({
        'displayName': 'New Admin',
        'lastName': 'Blah Name',
        'emails': ['Blah@blah.blah'],
        'avatar': 'blah avatar',
        'id': 'unit_test_person'
    })}
)
def test_add_admin_no_tags():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown="Nobody was tagged to be added. Please tag who you would like to add",
               roomId='BLAH'
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[1]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'add admin Unit Test Person'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot add admin Unit Test Person",
      "personId": "test_add_admin_2_tags",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id",
        "test_add_admin_2_tags2",
        "test_add_admin_2_tags3",
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_add_admin_2_tags'],
    project={'BLAH': 'UNIT_TEST'},
    queue=[],
    mock_people={'unit_test_person': AttrDict({
        'displayName': 'New Admin',
        'lastName': 'Blah Name',
        'emails': ['Blah@blah.blah'],
        'avatar': 'blah avatar',
        'id': 'unit_test_person'
    })}
)
def test_add_admin_2_tags():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown="Too many people were tagged. Please only tag one person at a time to be added",
               roomId='BLAH'
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'add admin Unit Test Person'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot remove admin Unit Test Person",
      "personId": "test_remove_admin",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id",
        "unit_test_person"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_remove_admin', 'unit_test_person'],
    project={'BLAH': 'UNIT_TEST'},
    queue=[],
    mock_people={'unit_test_person': AttrDict({
        'displayName': 'New Admin',
        'lastName': 'Blah Name',
        'emails': ['Blah@blah.blah'],
        'avatar': 'blah avatar',
        'id': 'unit_test_person'
    })}
)
def test_remove_admin():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 2, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args_list[0] == \
           mock.call(
               markdown="Removed 'New Admin' as an admin.",
               roomId='BLAH'
           ), "Sent message not correct"
    assert CiscoSparkAPI().messages.create.call_args_list[1] == \
           mock.call(
               markdown="Admins for 'UNIT_TEST' are:\n"
                        "- Unit Test Display Name\n"
                        "- Unit Test Display Name\n",
               roomId='BLAH'
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[4]
    assert ['test_remove_admin'] == args[0]

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'remove admin Unit Test Person'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot remove admin Unit Test Person",
      "personId": "test_remove_admin",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id",
        "unit_test_person"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_remove_admin'],
    project={'BLAH': 'UNIT_TEST'},
    queue=[],
    mock_people={'unit_test_person': AttrDict({
        'displayName': 'New Admin',
        'lastName': 'Blah Name',
        'emails': ['Blah@blah.blah'],
        'avatar': 'blah avatar',
        'id': 'unit_test_person'
    })}
)
def test_remove_admin_not_an_admin():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args_list[0] == \
           mock.call(
               markdown="'New Admin' is not an admin on this project",
               roomId='BLAH'
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[1]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'remove admin Unit Test Person'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot remove admin Unit Test Person",
      "personId": "test_remove_admin",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id",
        "unit_test_person",
        "unit_test_person2"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_remove_admin', 'unit_test_person'],
    project={'BLAH': 'UNIT_TEST'},
    queue=[],
    mock_people={'unit_test_person': AttrDict({
        'displayName': 'New Admin',
        'lastName': 'Blah Name',
        'emails': ['Blah@blah.blah'],
        'avatar': 'blah avatar',
        'id': 'unit_test_person'
    })}
)
def test_remove_admin_2_tags():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args_list[0] == \
           mock.call(
               markdown="Too many people were tagged. Please only tag one person at a time to be removed",
               roomId='BLAH'
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[1]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'remove admin Unit Test Person'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot remove admin Unit Test Person",
      "personId": "test_remove_admin",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id",
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_remove_admin', 'unit_test_person'],
    project={'BLAH': 'UNIT_TEST'},
    queue=[],
    mock_people={'unit_test_person': AttrDict({
        'displayName': 'New Admin',
        'lastName': 'Blah Name',
        'emails': ['Blah@blah.blah'],
        'avatar': 'blah avatar',
        'id': 'unit_test_person'
    })}
)
def test_remove_admin_no_tags():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args_list[0] == \
           mock.call(
               markdown="Nobody was tagged to be removed. Please tag who you would like to remove",
               roomId='BLAH'
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[1]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'remove admin Unit Test Person'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot remove person UNIT_TEST_PERSON",
      "personId": "test_remove_person",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id",
        "unit_test_person"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_remove_person'],
    project={'BLAH': 'UNIT_TEST'},
    queue=[{
        "atHeadTime": "2018-04-09 14:25:26.538711",
        "displayName": "Ava Test",
        "personId": "ava_test_id",
        "timeEnqueued": "2018-04-09 14:25:26.538673"
    },{
        "atHeadTime": None,
        "personId": "unit_test_person",
        "displayName": "Blah",
        "timeEnqueued": "2018-04-09 14:37:07.545799"
    }],
    mock_people={'unit_test_person': AttrDict({
        'displayName': 'Blah',
        'lastName': 'Blah Name',
        'emails': ['Blah@blah.blah'],
        'avatar': 'blah avatar'
    })}
)
def test_remove_person():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 2, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args_list[0] == \
           mock.call(
               markdown="Removing 'Blah'",
               roomId='BLAH'
           ), "Sent message not correct"
    assert CiscoSparkAPI().messages.create.call_args_list[1] == \
           mock.call(
               markdown="Current queue is:\n\n1. Ava Test (02:25:26 PM on Mon, Apr 09)\n",
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args_list[4]
    assert [{
        'atHeadTime': '2018-04-09 14:25:26.538711',
        'displayName': 'Ava Test',
        'personId': 'ava_test_id',
        'timeEnqueued': '2018-04-09 14:25:26.538673'
    }] == args[0]

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'remove person UNIT_TEST_PERSON'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot remove person UNIT_TEST_PERSON",
      "personId": "test_remove_person_no_in_queue",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id",
        "unit_test_person"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_remove_person_no_in_queue'],
    project={'BLAH': 'UNIT_TEST'},
    queue=[{
        "atHeadTime": "2018-04-09 14:25:26.538711",
        "displayName": "Ava Test",
        "personId": "ava_test_id",
        "timeEnqueued": "2018-04-09 14:25:26.538673"
    },{
        "atHeadTime": None,
        "personId": "unit_test_person2",
        "displayName": "Blah",
        "timeEnqueued": "2018-04-09 14:37:07.545799"
    }],
    mock_people={'unit_test_person': AttrDict({
        'displayName': 'Blah',
        'lastName': 'Blah Name',
        'emails': ['Blah@blah.blah'],
        'avatar': 'blah avatar'
    })}
)
def test_remove_person_no_in_queue():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 2, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args_list[0] == \
           mock.call(
               markdown="Removing 'Blah'",
               roomId='BLAH'
           ), "Sent message not correct"
    assert CiscoSparkAPI().messages.create.call_args_list[1] == \
           mock.call(
               markdown="ERROR: 'Blah' was not found in the queue",
               roomId='BLAH'
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'remove person UNIT_TEST_PERSON'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot remove person UNIT_TEST_PERSON",
      "personId": "test_remove_person_no_tags",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_remove_person_no_tags'],
    project={'BLAH': 'UNIT_TEST'},
    queue=[{
        "atHeadTime": "2018-04-09 14:25:26.538711",
        "displayName": "Ava Test",
        "personId": "ava_test_id",
        "timeEnqueued": "2018-04-09 14:25:26.538673"
    },{
        "atHeadTime": None,
        "personId": "unit_test_person",
        "displayName": "Blah",
        "timeEnqueued": "2018-04-09 14:37:07.545799"
    }],
)
def test_remove_person_no_tags():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown="Nobody was tagged to be removed. Please tag who you would like to remove",
               roomId='BLAH'
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'remove person UNIT_TEST_PERSON'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot remove person UNIT_TEST_PERSON",
      "personId": "test_remove_person_2_tags",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id",
        "test_remove_person_2_tags",
        "test_remove_person_2_tags2222"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_remove_person_2_tags'],
    project={'BLAH': 'UNIT_TEST'},
    queue=[{
        "atHeadTime": "2018-04-09 14:25:26.538711",
        "displayName": "Ava Test",
        "personId": "ava_test_id",
        "timeEnqueued": "2018-04-09 14:25:26.538673"
    },{
        "atHeadTime": None,
        "personId": "unit_test_person",
        "displayName": "Blah",
        "timeEnqueued": "2018-04-09 14:37:07.545799"
    }],
)
def test_remove_person_2_tags():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown="Too many people were tagged. Please only tag one person at a time to be removed",
               roomId='BLAH'
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'remove person UNIT_TEST_PERSON'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show people",
      "personId": "test_show_people",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_show_people'],
    project={'BLAH': 'UNIT_TEST'},
    people=[{
        "sparkId": "me_id",
        "displayName": "Ava Thorn"
    }, {
        "sparkId": "me_id2",
        "displayName": "Ava Thorn2"
    }]
)
def test_show_people():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown="All people that have used this bot for project 'UNIT_TEST' are:\n"
                        "1. Ava Thorn\n"
                        "2. Ava Thorn2\n"
                        "3. Unit Test Display Name\n",
               roomId='BLAH'
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show people'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot doesnt matter",
      "personId": "test_project_config_file_doesnt_exist",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}}
)
def test_no_files_exist():
    from endpoints import queue, CiscoSparkAPI
    with mock.patch("os.path.exists", return_value=False):
        queue()

    assert json.dump.call_args_list[0][0][0] == []
    assert json.dump.call_args_list[1][0][0] == {}
    assert len(json.dump.call_args_list[2][0][0]) == 1

    args, kwargs = json.dump.call_args_list[4]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'doesnt matter'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot get stats for commands issued",
      "personId": "test_get_stats_for_commands_issued",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_get_stats_for_commands_issued'],
    people=[{
        "sparkId": "blahblah",
        "displayName": "display blah",
        "commands": 1,
    }]
)
def test_get_stats_for_commands_issued():
    from endpoints import queue, CiscoSparkAPI
    queue()
    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown="```\n        PERSON         | COMMANDS ISSUED\n"
                        "     display blah      |        1       \n"
                        "Unit Test Display Name |        1       \n",
               roomId='BLAH'
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'get stats for commands issued'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot get stats for invalid stat",
      "personId": "test_get_stats_for_invalid_stat",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_get_stats_for_invalid_stat']
)
def test_get_stats_for_invalid_stat():
    from endpoints import queue, CiscoSparkAPI
    queue()
    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown="Column 'invalid stat' is not a valid column. Try one of: "
                        "PERSON, AVERAGE TIME IN QUEUE, AVERAGE TIME AT QUEUE HEAD, "
                        "COMMANDS ISSUED, NUMBER OF TIMES IN QUEUE, TOTAL TIME IN QUEUE, "
                        "TOTAL TIME AT QUEUE HEAD",
               roomId='BLAH'
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'get stats for invalid stat'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot foobar",
      "personId": "test_nonexistent_command",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}}
)
def test_nonexistent_command():
    from endpoints import queue, CiscoSparkAPI
    queue()
    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown="Unrecognized Command: 'foobar'\n\nPlease use one of:\n- " + '\n- '.join(SUPPORTED_COMMANDS),
               roomId='BLAH'
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'foobar'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot add person UNIT_TEST_PERSON",
      "personId": "test_add_person_no_tag",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_add_person_no_tag'],
    project={'BLAH': 'UNIT_TEST'},
    queue=[],
    mock_people={'unit_test_person': AttrDict({
        'displayName': 'Blah',
        'lastName': 'Blah Name',
        'emails': ['Blah@blah.blah'],
        'avatar': 'blah avatar'
    })}
)
def test_add_person_no_tag():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown="Nobody was tagged to be added. Please tag who you would like to add",
               roomId='BLAH'
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'add person UNIT_TEST_PERSON'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot foobar",
      "personId": "test_nonexistent_command",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}}
)
def test_nonexistent_command():
    from endpoints import queue, CiscoSparkAPI
    queue()
    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown="Unrecognized Command: 'foobar'\n\nPlease use one of:\n- " + '\n- '.join(SUPPORTED_COMMANDS),
               roomId='BLAH'
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'foobar'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot add person UNIT_TEST_PERSON BLAH",
      "personId": "test_add_person_2_tags",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id",
        "test_add_person_2_tags",
        "test_add_person_2_tags2"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_add_person_2_tags'],
    project={'BLAH': 'UNIT_TEST'}
)
def test_add_person_2_tags():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown="Too many people were tagged. Please only tag one person at a time to be added",
               roomId='BLAH'
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'add person UNIT_TEST_PERSON BLAH'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot get all stats as csv",
      "personId": "test_get_stats_as_csv",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_get_stats_as_csv'],
    project={'BLAH': 'UNIT_TEST'},
    people=[{
        "sparkId": "unit_test1",
        "displayName": "Blah",
        "currentlyInQueue": True,
        "totalTimeInQueue": 50,
        "totalTimeAtHead": 50,
        "number_of_times_in_queue": 1,
        "commands": 4
    }],
    queue=[{
        "atHeadTime": "1980-01-01 11:30:00.000000",
        "displayName": "Blah",
        "personId": "unit_test1",
        "timeEnqueued": "1980-01-01 11:00:00.000000"
    }]
)
def test_get_stats_as_csv():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown="Here are all the stats for project 'UNIT_TEST' as a csv",
               roomId='BLAH',
               files=['UNIT_TEST-STATISTICS.csv']
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'get all stats as csv'