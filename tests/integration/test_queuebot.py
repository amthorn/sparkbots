import flask
import ciscosparkapi
import json

from queuebot.decorators import with_request
from unittest import mock
from contextlib import contextmanager
from tests.scaffolding import CAT_FACT, DAD_JOKE
from app import VERSION, RELEASED, AUTHOR, EMAIL, QUEUE_THRESHOLD
from freezegun import freeze_time
from attrdict import AttrDict

def test_empty_data():
    with mock.patch("flask.request") as mock_api:
        flask.request.json={}
        with mock.patch("ciscosparkapi.CiscoSparkAPI") as mock_api:
            from endpoints import queue
            queue()


@freeze_time("1980-01-01 12:00:00.000000")
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


@freeze_time("1980-01-01 12:00:00.000000")
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


@freeze_time("1980-01-01 12:00:00.000000")
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
    project=[('UNIT_TEST', 'BLAH')]
)
def test_queue_status_ok():
    from endpoints import queue, CiscoSparkAPI
    queue()
    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='STATUS: Thank you for asking, nobody really asks anymore. '
                        'I guess I\'m okay, I just have a lot going on, you know? '
                        'I\'m supposed to be managing all the queues for people and '
                        'it\'s so hard because I have to be constantly paying attention '
                        'to every chatroom at all hours of the day, I get no sleep and '
                        'my social life has plumetted. But I guess I\'m:\n\n200 OK',
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args
    commands = args[0]
    assert commands[-1]['sparkId'] == 'message-id' and commands[-1]['command'] == 'status'


@freeze_time("1980-01-01 12:00:00.000000")
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
    project=[('UNIT_TEST', 'BLAH')],
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
    project=[('UNIT_TEST', 'BLAH')],
    queue=[{
        "atHeadTime": "1980-01-01 11:30:00.000000",
        "displayName": "Blah",
        "personId": "test_how_long_nonadmin_nonempty_queue",
        "timeEnqueued": "1980-01-01 11:00:00.000000"
    }],
    people=[{
        "sparkId": "test_how_long_nonadmin_nonempty_queue",
        "displayName": "Unit Test Person",
        "project": "UNIT_TEST",
        "totalTimeInQueue": 1000,
        "totalTimeAtHead": 900,
        "currentlyInQueue": True,
        "admin": False,
        "commands": 5,
        "number_of_times_in_queue": 2,
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
               markdown='Given that there are 0 people ahead of you. '
                        'Estimated wait time for "Unit Test Person" is:\n\n0:00:00',
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
      "text": "QueueBot help",
      "personId": "non-admin",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    project=[('UNIT_TEST', 'BLAH')]
)
def test_queue_help_unregistered():
    from endpoints import queue, CiscoSparkAPI
    from queuebot import Bot
    import endpoints
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    args, kwargs =  CiscoSparkAPI().messages.create.call_args
    assert 'This bot is to be used to manage a queue for a given team.' in kwargs['markdown'], "Sent message not correct"
    assert 'Available commands are:' in kwargs['markdown'], "Sent message not correct"
    args, kwargs = json.dump.call_args
    commands = args[0]
    assert commands[-1]['sparkId'] == 'message-id' and commands[-1]['command'] == 'help'


@freeze_time("1980-01-01 12:00:00.000000")
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
    project=[('UNIT_TEST', 'BLAH')],
    random=1
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


@freeze_time("1980-01-01 12:00:00.000000")
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
    project=[('UNIT_TEST', 'BLAH')]
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


@freeze_time("1980-01-01 12:00:00.000000")
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
    project=[('UNIT_TEST', 'BLAH')]
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


@freeze_time("1980-01-01 12:00:00.000000")
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
    project=[('UNIT_TEST', 'BLAH')],
    admins=['admin']
)
def test_admin_command_by_admin():
    from endpoints import queue, CiscoSparkAPI
    queue()
    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    args, kwargs = CiscoSparkAPI().messages.create.call_args
    assert 'Admin commands can be used in any room' in kwargs['markdown'], "Sent message not correct"
    assert 'Available admin commands are:' in kwargs['markdown'], "Sent message not correct"
    args, kwargs = json.dump.call_args
    commands = args[0]
    assert commands[-1]['sparkId'] == 'message-id' and commands[-1]['command'] == 'show admin commands'


@freeze_time("1980-01-01 12:00:00.000000")
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
    project=[('UNIT_TEST', 'BLAH')]
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


@freeze_time("1980-01-01 12:00:00.000000")
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
    project=[('UNIT_TEST', 'BLAH')]
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


@freeze_time("1980-01-01 12:00:00.000000")
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
    project=[('UNIT_TEST', 'BLAH')],
    queue=[{
        "personId": "fooid",
        "timeEnqueued": "2018-04-06 12:34:45.678901",
        "displayName": "Unit Test Display Name",
        "atHeadTime": "2018-04-06 12:31:26.851938"
    }],
    people=[
        {
            'sparkId': 'fooid',
            'number_of_times_in_queue': 1,
            'totalTimeAtHead': 5
        }
    ]
)
def test_list_one_member():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='Current queue on subproject "GENERAL" is:\n\n'
                        '1. Unit Test Display Name (12:34:45 PM on Fri, Apr 06)\n\n\n'
                        'Given that there is 1 person in the queue. '
                        'Estimated wait time from the back of the queue is:\n\n0:00:05',
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
      "text": "QueueBot list for subproject other_subproject",
      "personId": "test_list_one_member_for_subproject",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    project=[('UNIT_TEST', 'BLAH')],
    queue=[{
        "personId": "fooid",
        "timeEnqueued": "2018-04-06 12:34:45.678901",
        "displayName": "Unit Test Display Name",
        "atHeadTime": "2018-04-06 12:31:26.851938"
    }],
    people=[
        {
            'sparkId': 'fooid',
            'number_of_times_in_queue': 1,
            'totalTimeAtHead': 5
        }
    ],
    subprojects=['GENERAL', 'OTHER_SUBPROJECT']
)
def test_list_one_member_for_subproject():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='Current queue on subproject "OTHER_SUBPROJECT" is:\n\n'
                        '1. Unit Test Display Name (12:34:45 PM on Fri, Apr 06)\n\n\n'
                        'Given that there is 1 person in the queue. Estimated wait time '
                        'from the back of the queue is:\n\n0:00:05',
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
      "text": "QueueBot list",
      "personId": "test_list_no_default_subproject",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    project=[('UNIT_TEST', 'BLAH')],
    queue=[{
        "personId": "fooid",
        "timeEnqueued": "2018-04-06 12:34:45.678901",
        "displayName": "Unit Test Display Name",
        "atHeadTime": "2018-04-06 12:31:26.851938"
    }],
    people=[
        {
            'sparkId': 'fooid',
            'number_of_times_in_queue': 1,
            'totalTimeAtHead': 5
        }
    ],
    subprojects=['GENERAL', 'OTHER_SUBPROJECT'],
    settings={
        'default_subproject': None
    }
)
def test_list_no_default_subproject():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='There is no default subproject for project "UNIT_TEST". '
                        'You must set a default subproject or specify a subproject.',
               roomId='BLAH'
           ), "Sent message not correct"


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot list for subproject invalid",
      "personId": "test_list_invalid_subproject",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    project=[('UNIT_TEST', 'BLAH')],
    queue=[{
        "personId": "fooid",
        "timeEnqueued": "2018-04-06 12:34:45.678901",
        "displayName": "Unit Test Display Name",
        "atHeadTime": "2018-04-06 12:31:26.851938"
    }],
    people=[
        {
            'sparkId': 'fooid',
            'number_of_times_in_queue': 1,
            'totalTimeAtHead': 5
        }
    ],
    subprojects=['GENERAL', 'OTHER_SUBPROJECT'],
)
def test_list_invalid_subproject():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='"INVALID" is not a subproject on project "UNIT_TEST"',
               roomId='BLAH'
           ), "Sent message not correct"


@freeze_time("1980-01-01 12:00:00.000000")
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
    project=[('UNIT_TEST', 'BLAH')],
    queue=[{
        "personId": "fooid",
        "timeEnqueued": "2018-04-06 12:34:45.678901",
        "displayName": "Unit Test Display Name",
        "atHeadTime": "1980-01-01 11:00:00.000000"
    },{
        "personId": "fooid2",
        "timeEnqueued": "2018-04-07 12:34:45.678901",
        "displayName": "Unit Test Display Name 2",
        "atHeadTime": None
    }],
    people=[
        {
            'sparkId': 'fooid',
            'number_of_times_in_queue': 2,
            'totalTimeAtHead': 5
        },
        {
            'sparkId': 'fooid2',
            'number_of_times_in_queue': 2,
            'totalTimeAtHead': 5
        }]
)
def test_list_two_members():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='Current queue on subproject "GENERAL" is:\n\n'
                        '1. Unit Test Display Name (12:34:45 PM on Fri, Apr 06)\n'
                        '2. Unit Test Display Name 2 (12:34:45 PM on Sat, Apr 07)'
                        '\n\n\nGiven that there are 2 people in the queue. '
                        'Estimated wait time from the back of the queue is:\n\n0:00:02.500000',
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
    project=[('UNIT_TEST', 'BLAH')],
    queue=[],
    global_stats={
        'historicalData': {
            'queues': {},
            'flush_times': {},
            'mostActiveQueueUsers': {},
            'quickestAtHeadUsers': {},
            'largestQueueDepths': {},
            'largestQueueDepthTimes': {}
        },
        'maxQueueDepthByHour': {},
        'maxQueueDepthByDay': {},
        'minQueueDepthByHour': {},
        'minQueueDepthByDay': {},
        'minFlushTimeByHour': {},
        'minFlushTimeByDay': {},
        'maxFlushTimeByHour': {},
        'maxFlushTimeByDay': {},
        'largestQueueDepth':   0,
        'largestQueueDepthTime': '1980-01-01 10:00:00.000000',
    }
)
def test_add_me_empty_queue():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='Adding "Unit Test Display Name"\n\nCurrent queue on subproject "GENERAL" is:\n\n'
                        '1. Unit Test Display Name (12:00:00 PM on Tue, Jan 01)\n\n\n'
                        'Given that there is 1 person in the queue. '
                        'Estimated wait time from the back of the queue is:\n\n0:00:00',
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
    project=[('UNIT_TEST', 'BLAH')],
    queue=[{
        "personId": "first-id",
        "timeEnqueued": "2018-04-06 12:31:22.458645",
        "displayName": "Unit Test Display Name 1",
        "atHeadTime": "1980-01-01 11:00:00.000000"
    }],
    global_stats={
        'historicalData': {
            'queues': {},
            'flush_times': {},
            'mostActiveQueueUsers': {},
            'quickestAtHeadUsers': {},
            'largestQueueDepths': {},
            'largestQueueDepthTimes': {}
        },
        'maxQueueDepthByHour': {},
        'minQueueDepthByHour': {},
        'minFlushTimeByHour': {},
        'maxFlushTimeByHour': {},
        'maxQueueDepthByDay': {},
        'minQueueDepthByDay': {},
        'minFlushTimeByDay': {},
        'maxFlushTimeByDay': {},
        'largestQueueDepth':   0,
        'largestQueueDepthTime': '1980-01-01 10:00:00.000000'
    },
    people=[{
        'sparkId': 'first-id',
        'number_of_times_in_queue': 0,
        'totalTimeInQueue': 30,
        'totalTimeAtHead': 30,
        'added_to_queue': [
            '1980-01-01 11:00:00.000000'
        ],
        'removed_from_queue': []
    }]
)
def test_add_me_one_in_queue():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='Adding "Unit Test Display Name"\n\nCurrent queue on subproject "GENERAL" is:\n\n'
                        '1. Unit Test Display Name 1 (12:31:22 PM on Fri, Apr 06)\n'
                        '2. Unit Test Display Name (12:00:00 PM on Tue, Jan 01)\n\n\n'
                        'Given that there are 2 people in the queue. Estimated wait time '
                        'from the back of the queue is:\n\n0:00:00',
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
    project=[('UNIT_TEST', 'BLAH')],
    queue=[{
        "personId": "test_remove_me_one_in_queue",
        "timeEnqueued": "2018-04-06 12:31:22.458645",
        "displayName": "Unit Test Display Name",
        "atHeadTime": "2018-04-06 12:31:26.851938"
    }],
    global_stats={
        'historicalData': {
            'queues': {},
            'flush_times': {},
            'mostActiveQueueUsers': {},
            'quickestAtHeadUsers': {},
            'largestQueueDepths': {},
            'largestQueueDepthTimes': {}
        },
        'maxQueueDepthByHour': {},
        'minQueueDepthByHour': {},
        'minFlushTimeByHour': {},
        'maxFlushTimeByHour': {},
        'maxQueueDepthByDay': {},
        'minQueueDepthByDay': {},
        'minFlushTimeByDay': {},
        'maxFlushTimeByDay': {},
        'largestQueueDepth':   0,
        'largestQueueDepthTime': '1980-01-01 10:00:00.000000'
    }
)
def test_remove_me_one_in_queue():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='Removing "Unit Test Display Name"\n\nCurrent queue on subproject "GENERAL" is:\n\n'
                        'There is no one in the queue\n\nGiven that there are 0 people in the queue. '
                        'Estimated wait time from the back of the queue is:\n\n0:00:00',
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
    project=[('UNIT_TEST', 'BLAH')],
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
    global_stats={
        'historicalData': {
            'queues': {},
            'flush_times': {},
            'mostActiveQueueUsers': {},
            'quickestAtHeadUsers': {},
            'largestQueueDepths': {},
            'largestQueueDepthTimes': {}
        },
        'maxQueueDepthByHour': {},
        'minQueueDepthByHour': {},
        'minFlushTimeByHour': {},
        'maxFlushTimeByHour': {},
        'maxQueueDepthByDay': {},
        'minQueueDepthByDay': {},
        'minFlushTimeByDay': {},
        'maxFlushTimeByDay': {},
        'largestQueueDepth':   0,
        'largestQueueDepthTime': '1980-01-01 10:00:00.000000'
    },
    people=[{
        'sparkId': 'test_remove_me_one_in_queue2',
        'number_of_times_in_queue': 1,
        'totalTimeAtHead': 30,
        'added_to_queue': [
            '2018-04-06 12:31:22.458645'
        ],
        'removed_from_queue': []
    }]
)
def test_remove_me_two_in_queue_me_at_head():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='Removing "Unit Test Display Name"\n\nCurrent queue on subproject "GENERAL" is:\n\n'
                        '1. Unit Test Display Name (12:31:22 PM on Fri, Apr 06)\n\n\n'
                        'Given that there is 1 person in the queue. Estimated wait time '
                        'from the back of the queue is:\n\n0:00:30\n\n'
                        '<@personId:test_remove_me_one_in_queue2|Unit Test Display Name>, you\'re at the front of the queue!',
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args_list[0]
    assert 'test_remove_me_one_in_queue' in [i['sparkId'] for i in args[0]]

    args, kwargs = json.dump.call_args_list[4]
    assert len(args[0]) == 1

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'remove me'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot remove me",
      "personId": "test_remove_me_three_in_queue_me_at_head",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    project=[('UNIT_TEST', 'BLAH')],
    queue=[{
        "personId": "test_remove_me_three_in_queue_me_at_head",
        "timeEnqueued": "2018-04-06 12:31:22.458645",
        "displayName": "Unit Test Display Name",
        "atHeadTime": "2018-04-06 12:31:26.851938"
    }, {
        "personId": "test_remove_me_one_in_queue2",
        "timeEnqueued": "2018-04-06 12:31:22.458645",
        "displayName": "Unit Test Display Name",
        "atHeadTime": None
    }, {
        "personId": "test_remove_me_one_in_queue2",
        "timeEnqueued": "2018-04-06 12:31:22.458645",
        "displayName": "Unit Test Display Name",
        "atHeadTime": None
    }],
    global_stats={
        'historicalData': {
            'queues': {
                '2018-04-06 12:31:22.458645': {}
            },
            'flush_times': {},
            'mostActiveQueueUsers': {},
            'quickestAtHeadUsers': {},
            'largestQueueDepths': {},
            'largestQueueDepthTimes': {}
        },
        'maxQueueDepthByHour': {},
        'minQueueDepthByHour': {},
        'minFlushTimeByHour': {},
        'maxFlushTimeByHour': {},
        'maxQueueDepthByDay': {},
        'minQueueDepthByDay': {},
        'minFlushTimeByDay': {},
        'maxFlushTimeByDay': {},
        'largestQueueDepth':   0,
        'largestQueueDepthTime': '1980-01-01 10:00:00.000000'
    },
    people=[{
        'sparkId': 'test_remove_me_one_in_queue2',
        'number_of_times_in_queue': 1,
        'totalTimeAtHead': 30,
        'added_to_queue': [
            '2018-04-06 12:31:22.458645'
        ],
        'removed_from_queue': []
    }]
)
def test_remove_me_three_in_queue_me_at_head():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='Removing "Unit Test Display Name"\n\nCurrent queue on subproject "GENERAL" is:\n\n'
                        '1. Unit Test Display Name (12:31:22 PM on Fri, Apr 06)\n'
                        '2. Unit Test Display Name (12:31:22 PM on Fri, Apr 06)\n\n\n'
                        'Given that there are 2 people in the queue. Estimated wait '
                        'time from the back of the queue is:\n\n0:01:00\n\n'
                        '<@personId:test_remove_me_one_in_queue2|Unit Test Display Name>, you\'re at the front of the queue!',
               roomId='BLAH'
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[0]
    assert 'test_remove_me_three_in_queue_me_at_head' in [i['sparkId'] for i in args[0]]

    args, kwargs = json.dump.call_args_list[4]
    assert len(args[0]) == 2

    args, kwargs = json.dump.call_args_list[2]
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
    project=[('UNIT_TEST', 'BLAH')],
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

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown="ERROR: 'Unit Test Display Name' was not found in the queue",
               roomId='BLAH'
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[0]
    assert 'test_remove_me_one_in_queue_but_not_caller' in [i['sparkId'] for i in args[0]]

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'remove me'


@freeze_time("1980-01-01 12:00:00.000000")
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
    project=[('UNIT_TEST', 'BLAH')],
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
               markdown="Admins for 'UNIT_TEST' are:\n- Unit Test Display Name (global)\n",
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args_list[0]
    assert 'test_show_admins' in [i['sparkId'] for i in args[0]]

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show admins'


@freeze_time("1980-01-01 12:00:00.000000")
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
               markdown="ERROR: project \"LALALA\" has not been created.",
               roomId='BLAH'
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'register bot to project lalala'


@freeze_time("1980-01-01 12:00:00.000000")
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
               markdown="ERROR: project \"SHOULD_NOT_WORK\" has not been created.",
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and \
           args[0][-1]['command'] == 'register bot to project should_not_work'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show all stats as markdown",
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
    people=[],
    project=[('UNIT_TEST', 'BLAH')]
)
def test_get_all_stats():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown="Showing stats for subproject \"GENERAL\"\n\n```\n        PERSON         | AVERAGE TIME AT QUEUE HEAD | AVERAGE TIME IN "
                        "QUEUE | COMMANDS ISSUED | NUMBER OF TIMES IN QUEUE | TOTAL TIME AT QUEUE HEAD | "
                        "TOTAL TIME IN QUEUE\nUnit Test Display Name |         0 seconds          |     "
                        "  0 seconds       |        1        |            0             |        0 seco"
                        "nds         |      0 seconds     \n",
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and \
           args[0][-1]['command'] == 'show all stats as markdown'


@freeze_time("1980-01-01 12:00:00.000000")
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
    project=[('UNIT_TEST', 'BLAH')]
)
def test_show_registration():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 2, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args_list[0] == \
           mock.call(
               markdown="QueueBot registration: UNIT_TEST",
               roomId='BLAH'
           ), "Sent message not correct"
    assert CiscoSparkAPI().messages.create.call_args_list[1] == \
           mock.call(
               markdown="Subprojects for project \"UNIT_TEST\" are:\n\n- GENERAL (DEFAULT)\n",
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
    project=[('UNIT_TEST', 'BLAH')],
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
               markdown="Last 10 commands for subproject \"GENERAL\" are:\n"
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
    project=[('UNIT_TEST', 'BLAH')],
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
               markdown="Last 10 commands for subproject \"GENERAL\" are:\n"
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
    global_stats={
        'historicalData': {
            'queues': {},
            'flush_times': {},
            'mostActiveQueueUsers': {},
            'quickestAtHeadUsers': {},
            'largestQueueDepths': {},
            'largestQueueDepthTimes': {}
        },
        'maxQueueDepthByHour': {},
        'minQueueDepthByHour': {},
        'minFlushTimeByHour': {},
        'maxFlushTimeByHour': {},
        'maxQueueDepthByDay': {},
        'minQueueDepthByDay': {},
        'minFlushTimeByDay': {},
        'maxFlushTimeByDay': {},
        'largestQueueDepth': 0,
        'largestQueueDepthTime': '1980-01-01 10:00:00.000000'
    },
    admins=['test_add_person'],
    project=[('UNIT_TEST', 'BLAH')],
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

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown="Adding \"Blah\"\n\nCurrent queue on subproject \"GENERAL\" is:\n\n"
                        "1. Blah (12:00:00 PM on Tue, Jan 01)\n\n\n"
                        "Given that there is 1 person in the queue. Estimated wait "
                        "time from the back of the queue is:\n\n0:00:00",
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
    project=[('UNIT_TEST', 'BLAH')],
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
                        "- New Admin\n\n"
                        "- Unit Test Display Name (global)\n",
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
    project=[('UNIT_TEST', 'BLAH')],
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
    project=[('UNIT_TEST', 'BLAH')],
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
    project=[('UNIT_TEST', 'BLAH')],
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
    project=[('UNIT_TEST', 'BLAH')],
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
                        "- Unit Test Display Name (global)\n",
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
    project=[('UNIT_TEST', 'BLAH')],
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
    project=[('UNIT_TEST', 'BLAH')],
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
    project=[('UNIT_TEST', 'BLAH')],
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
    global_stats={
        'historicalData': {
            'queues': {},
            'flush_times': {},
            'mostActiveQueueUsers': {},
            'quickestAtHeadUsers': {},
            'largestQueueDepths': {},
            'largestQueueDepthTimes': {}
        },
        'maxQueueDepthByHour': {},
        'minQueueDepthByHour': {},
        'minFlushTimeByHour': {},
        'maxFlushTimeByHour': {},
        'maxQueueDepthByDay': {},
        'minQueueDepthByDay': {},
        'minFlushTimeByDay': {},
        'maxFlushTimeByDay': {},
        'largestQueueDepth':   0,
        'largestQueueDepthTime': '1980-01-01 10:00:00.000000'
    },
    admins=['test_remove_person'],
    project=[('UNIT_TEST', 'BLAH')],
    queue=[{
        "atHeadTime": "1980-01-01 11:00:00.000000",
        "displayName": "Ava Test",
        "personId": "ava_test_id",
        "timeEnqueued": "1980-01-01 11:00:00.000000"
    },{
        "atHeadTime": None,
        "personId": "unit_test_person",
        "displayName": "Blah",
        "timeEnqueued": "1980-01-01 11:30:00.000000"
    }],
    people=[{
        'sparkId': 'ava_test_id',
        'number_of_times_in_queue': 3,
        'totalTimeInQueue': 30,
        'totalTimeAtHead': 30,
        'removed_from_queue': [],
        'added_to_queue': [
            '1980-01-01 11:00:00.000000'
        ]
    },{
        'sparkId': 'unit_test_person',
        'number_of_times_in_queue': 3,
        'totalTimeInQueue': 30,
        'totalTimeAtHead': 30,
        'removed_from_queue': [],
        'added_to_queue': [
            '1980-01-01 11:30:00.000000q'
        ]
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

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown="Removing \"Blah\"\n\nCurrent queue on subproject \"GENERAL\" is:\n\n1. Ava Test (11:00:00 AM on Tue, Jan 01)\n\n\n"
                        "Given that there is 1 person in the queue. Estimated wait time from "
                        "the back of the queue is:\n\n0:00:00\n\n"
                        "<@personId:ava_test_id|Ava Test>, you\'re at the front of the queue!",
               roomId='BLAH'
           ), "Sent message not correct"
    args, kwargs = json.dump.call_args_list[4]
    assert [{
        "atHeadTime": "1980-01-01 11:00:00.000000",
        "displayName": "Ava Test",
        "personId": "ava_test_id",
        "timeEnqueued": "1980-01-01 11:00:00.000000"
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
    project=[('UNIT_TEST', 'BLAH')],
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

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
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
    project=[('UNIT_TEST', 'BLAH')],
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
    project=[('UNIT_TEST', 'BLAH')],
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
    project=[('UNIT_TEST', 'BLAH')],
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
               markdown="All people that have used this bot for subproject \"GENERAL\" on project \"UNIT_TEST\" are:\n"
                        "1. Ava Thorn\n"
                        "2. Ava Thorn2\n"
                        "3. Unit Test Display Name\n",
               roomId='BLAH'
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show people'


# @freeze_time("1980-01-01 12:00:00.000000")
# @with_request(data={
#       "id": "message-id",
#       "roomId": "BLAH",
#       "roomType": "group",
#       "text": "QueueBot doesnt matter",
#       "personId": "test_project_config_file_doesnt_exist",
#       "mentionedPeople": [
#         "me_id"
#       ],
#       "created": "2018-04-02T14:23:08.086Z"
#     },
#     global_stats={'historicalData': {}}
# )
# def test_no_files_exist():
#     from endpoints import queue, CiscoSparkAPI
#     with mock.patch("os.path.exists", return_value=False):
#         queue()
#
#     assert json.dump.call_args_list[1][0][0] == []
#     assert json.dump.call_args_list[2][0][0] == {}
#     assert len(json.dump.call_args_list[3][0][0]) == 1
#
#     args, kwargs = json.dump.call_args_list[5]
#     assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'doesnt matter'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show stats for commands issued",
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
    }],
    project=[('UNIT_TEST', 'BLAH')]
)
def test_get_stats_for_commands_issued():
    from endpoints import queue, CiscoSparkAPI
    queue()
    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown="Showing stats for subproject \"GENERAL\"\n\n```\n        PERSON         | COMMANDS ISSUED\n"
                        "     display blah      |        1       \nUnit Test Display Name |        1       \n",
               roomId='BLAH'
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show stats for commands issued'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show stats for invalid stat",
      "personId": "test_get_stats_for_invalid_stat",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_get_stats_for_invalid_stat'],
    project=[('UNIT_TEST', 'BLAH')]
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
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show stats for invalid stat'


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
    global_stats={'historicalData': {}},
    project=[('UNIT_TEST', 'BLAH')]
)
def test_nonexistent_command():
    from endpoints import queue, CiscoSparkAPI
    queue()
    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    args, kwargs = CiscoSparkAPI().messages.create.call_args
    assert 'Unrecognized Command' in kwargs['markdown'], "Sent message not correct"

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
    project=[('UNIT_TEST', 'BLAH')],
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
    project=[('UNIT_TEST', 'BLAH')]
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
      "text": "QueueBot show all stats as csv",
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
    project=[('UNIT_TEST', 'BLAH')],
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
               markdown="Here are all the stats for subproject 'GENERAL' on project 'UNIT_TEST' as a csv",
               roomId='BLAH',
               files=['UNIT_TEST-GENERAL-STATISTICS.csv']
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show all stats as csv'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show most active users",
      "personId": "test_get_most_active_users",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}, 'mostActiveQueueUsers': ['unit_test1']},
    admins=['test_get_most_active_users'],
    project=[('UNIT_TEST', 'BLAH')],
    people=[{
        "sparkId": "unit_test1",
        "displayName": "Blah",
        "currentlyInQueue": True,
        "totalTimeInQueue": 50,
        "totalTimeAtHead": 50,
        "number_of_times_in_queue": 1,
        "commands": 4,
        'added_to_queue':[
            '1',
            '2',
            '3'
        ],
        'removed_from_queue': [
            '1',
            '2'
        ]
    },{
        "sparkId": "unit_test2",
        "displayName": "Blah2",
        "currentlyInQueue": True,
        "totalTimeInQueue": 50,
        "totalTimeAtHead": 50,
        "number_of_times_in_queue": 0,
        "commands": 4,
        'added_to_queue':[],
        'removed_from_queue': []
    }]
)
def test_get_most_active_users():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown="Most active user/s for subproject \"GENERAL\" on project UNIT_TEST is:\n\n- Blah (5 queue activities)\n",
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show most active users'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show largest queue depth",
      "personId": "test_largest_queue_depth",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={
        'historicalData': {},
        'maxQueueDepthByHour': {},
        'minQueueDepthByHour': {},
        'minFlushTimeByHour': {},
        'maxFlushTimeByHour': {},
        'largestQueueDepth': 5,
        'largestQueueDepthHour': '1970-01-01 12:00:00.000000'
    },
    admins=['test_largest_queue_depth'],
    project=[('UNIT_TEST', 'BLAH')]
)
def test_largest_queue_depth():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown="Largest queue depth for subproject \"GENERAL\" on project UNIT_TEST is:\n\n"
                        "**5** at 1970-01-01 12:00:00",
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show largest queue depth'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show quickest users",
      "personId": "test_largest_queue_depth",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}, 'quickestAtHeadUsers': ['unit_test']},
    admins=['test_largest_queue_depth'],
    project=[('UNIT_TEST', 'BLAH')],
    people=[{
        "sparkId": "unit_test",
        "displayName": "Blah2",
        "number_of_times_in_queue": 2,
        'totalTimeAtHead': 1234,
        'added_to_queue':[],
        'removed_from_queue': []
    }]
)
def test_quickest_at_head_user():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown="Quickest at head user/s for subproject \"GENERAL\" on project \"UNIT_TEST\" is:\n\n- Blah2 (0:10:17)\n",
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show quickest users'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show average queue depth by hour",
      "personId": "test_show_average_queue_depth",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}, 'averageQueueDepthByHour': {
        '1': 5
    },
                  'quickestAtHeadUsers': ['unit_test']},
    admins=['test_show_average_queue_depth'],
    project=[('UNIT_TEST', 'BLAH')],
)
def test_show_average_queue_depth():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               files=['get_average_queue_depth_hour_UNIT_TEST_GENERAL.png'],
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show average queue depth by hour'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show average queue depth by day",
      "personId": "test_show_average_queue_depth_day",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={
        'historicalData': {},
        'averageQueueDepthByDay': {
            '0': 5
        }
    },
    admins=['test_show_average_queue_depth_day'],
    project=[('UNIT_TEST', 'BLAH')],
)
def test_show_average_queue_depth_day():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               files=['get_average_queue_depth_day_UNIT_TEST_GENERAL.png'],
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show average queue depth by day'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show min queue depth by day",
      "personId": "test_show_min_queue_depth_day",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={
        'historicalData': {},
        'minQueueDepthByDay': {
            '0': 0,
        }
    },
    admins=['test_show_min_queue_depth_day'],
    project=[('UNIT_TEST', 'BLAH')],
)
def test_show_min_queue_depth_day():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               files=['get_min_queue_depth_day_UNIT_TEST_GENERAL.png'],
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show min queue depth by day'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show max queue depth by day",
      "personId": "test_show_max_queue_depth_day",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={
        'historicalData': {},
        'maxQueueDepthByDay': {
            '0': 30,
        }
    },
    admins=['test_show_max_queue_depth_day'],
    project=[('UNIT_TEST', 'BLAH')],
)
def test_show_max_queue_depth_day():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               files=['get_max_queue_depth_day_UNIT_TEST_GENERAL.png'],
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show max queue depth by day'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show max flush time by day",
      "personId": "test_show_max_flush_time_day",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={
        'historicalData': {},
        'maxFlushTimeByDay': {
            '0': 400,
            '1': 300,
            '2': 450,
            '3': 0,
            '4': 0,
            '5': 0,
            '6': 0
        }
    },
    admins=['test_show_max_flush_time_day'],
    project=[('UNIT_TEST', 'BLAH')],
)
def test_show_max_flush_time_day():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               files=['get_max_flush_time_day_UNIT_TEST_GENERAL.png'],
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show max flush time by day'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show min flush time by day",
      "personId": "test_show_min_flush_time_day",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={
        'historicalData': {},
        'minFlushTimeByDay': {
            '0': 400,
            '1': 300,
            '2': 450,
            '3': 0,
            '4': 0,
            '5': 0,
            '6': 0
        }
    },
    admins=['test_show_min_flush_time_day'],
    project=[('UNIT_TEST', 'BLAH')],
)
def test_show_min_flush_time_day():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               files=['get_min_flush_time_day_UNIT_TEST_GENERAL.png'],
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show min flush time by day'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show average flush time by day",
      "personId": "test_show_average_flush_time_day",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={
        'historicalData': {},
        'averageFlushTimeByDay': {
            '0': 400,
            '1': 300,
            '2': 450,
            '3': 0,
            '4': 0,
            '5': 0,
            '6': 0
        }
    },
    admins=['test_show_average_flush_time_day'],
    project=[('UNIT_TEST', 'BLAH')],
)
def test_show_average_flush_time_day():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               files=['get_average_flush_time_day_UNIT_TEST_GENERAL.png'],
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show average flush time by day'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show max queue depth by hour",
      "personId": "test_show_max_queue_depth",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}, 'averageQueueDepthByHour': {
        1: 5
    }, 'maxQueueDepthByHour': {'0': 5},
                  'quickestAtHeadUsers': ['unit_test']},
    admins=['test_show_max_queue_depth'],
    project=[('UNIT_TEST', 'BLAH')],
)
def test_show_max_queue_depth():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               files=['get_max_queue_depth_hour_UNIT_TEST_GENERAL.png'],
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show max queue depth by hour'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show min queue depth by hour",
      "personId": "test_show_min_queue_depth",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}, 'averageQueueDepthByHour': {
        1: 5
    }, 'minQueueDepthByHour': {'0': 5},
                  'quickestAtHeadUsers': ['unit_test']},
    admins=['test_show_min_queue_depth'],
    project=[('UNIT_TEST', 'BLAH')],
)
def test_show_min_queue_depth():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               files=['get_min_queue_depth_hour_UNIT_TEST_GENERAL.png'],
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show min queue depth by hour'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show min flush time by hour",
      "personId": "test_show_min_flush_time",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}, 'averageQueueDepthByHour': {
        1: 5
    }, 'minFlushTimeByHour': {'0': 5},
                  'quickestAtHeadUsers': ['unit_test']},
    admins=['test_show_min_flush_time'],
    project=[('UNIT_TEST', 'BLAH')],
)
def test_show_min_flush_time():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               files=['get_min_flush_time_hour_UNIT_TEST_GENERAL.png'],
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show min flush time by hour'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show max flush time by hour",
      "personId": "test_show_max_flush_time",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}, 'averageQueueDepthByHour': {
        1: 5
    }, 'maxFlushTimeByHour': {'0': 5},
                  'quickestAtHeadUsers': ['unit_test']},
    admins=['test_show_max_flush_time'],
    project=[('UNIT_TEST', 'BLAH')],
)
def test_show_max_flush_time():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               files=['get_max_flush_time_hour_UNIT_TEST_GENERAL.png'],
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show max flush time by hour'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show average flush time by hour",
      "personId": "test_show_average_flush_time",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {'queues': {}, 'flush_times': {
            "2018-04-11 12:29:32.761368": 789.48,
            "2018-04-11 12:29:39.560015": 526.32,
            "2018-04-11 12:29:42.472131": 263.16,
            "2018-04-11 12:41:53.973779": 263.16,
            "2018-04-11 12:42:23.145446": 263.16,
            "2018-04-11 12:52:25.279070": 0,
            "2018-04-11 12:52:28.215140": 250.0
    }, 'mostActiveQueueUsers': {},
                                     'quickestAtHeadUsers': {}, 'largestQueueDepths': {},
                                     'largestQueueDepthTimes': {}},
                  'averageQueueDepthByHour': {
        1: 5
    }, 'averageFlushTimeByHour': {'0': 5},
                  'quickestAtHeadUsers': ['unit_test'], 'largestQueueDepth': {}, 'largestQueueDepthTime': {},
                  'maxQueueDepthByHour': {}, 'minQueueDepthByHour': {},
                  'maxFlushTimeByHour': {}, 'minFlushTimeByHour': {}},
    admins=['test_show_average_flush_time'],
    project=[('UNIT_TEST', 'BLAH')],
)
def test_show_average_flush_time():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               files=['get_average_flush_time_hour_UNIT_TEST_GENERAL.png'],
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show average flush time by hour'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show version",
      "personId": "test_show_version_number",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_show_version_number'],
    project=[('UNIT_TEST', 'BLAH')],
)
def test_show_version_number():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown=VERSION,
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show version'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show all release notes",
      "personId": "test_show_release_notes",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_show_release_notes'],
    project=[('UNIT_TEST', 'BLAH')],
)
def test_show_release_notes():
    from endpoints import queue, CiscoSparkAPI
    from app import RELEASE_NOTES
    r_notes = json.load(open(RELEASE_NOTES))
    message = ''
    for version, notes in r_notes.items():
        message += '\n\n**' + version + '**\n\n' + notes
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown=message,
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show all release notes'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show release notes for 1.1.0",
      "personId": "test_show_release_notes",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_show_release_notes_for_valid'],
    project=[('UNIT_TEST', 'BLAH')],
)
def test_show_release_notes_for_valid():
    from endpoints import queue, CiscoSparkAPI
    from app import RELEASE_NOTES
    notes = json.load(open(RELEASE_NOTES))
    message = '\n\n**1.1.0**\n\n' + notes['1.1.0']
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown=message,
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[1]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show release notes for 1.1.0'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show release notes for invalid.number",
      "personId": "test_show_release_notes_for_invalid",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_show_release_notes_for_invalid'],
    project=[('UNIT_TEST', 'BLAH')],
)
def test_show_release_notes_for_invalid():
    from endpoints import queue, CiscoSparkAPI
    from app import RELEASE_NOTES
    notes = json.load(open(RELEASE_NOTES))
    message = '"invalid.number" is not a valid release. Please use one of:\n\n- ' + '\n- '.join(notes.keys())
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown=message,
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show release notes for invalid.number'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show projects",
      "personId": "test_show_projects",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_show_projects'],
    project=[('UNIT_TEST', 'BLAH')],
)
def test_show_projects_not_global_admin():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='You are not registered as a global admin.',
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show projects'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show projects",
      "personId": "Y2lzY29zcGFyazovL3VzL1BFT1BMRS9kODRkZjI1MS1iYmY3LTRlZTEtOTM1OS00Y2I0MGIyOTBhN2I",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData': {}},
    admins=['test_show_projects'],
    project=[('UNIT_TEST', 'BLAH')],
)
def test_show_projects_is_global_admin():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='Registered projects are:\n\n- UNIT_TEST (1 room/s; 1 subproject/s; 1980-01-01 12:00:00)\n',
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show projects'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot add me",
      "personId": "test_add_me_queue_at_max",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData':{'queues': {}, 'flush_times': {},
                                    'mostActiveQueueUsers': {}, 'quickestAtHeadUsers': {}, 'largestQueueDepths': {},
                                    'largestQueueDepthTimes': {}},
                  'maxQueueDepthByHour': {}, 'minQueueDepthByHour': {}, 'minFlushTimeByHour': {}, 'maxFlushTimeByHour': {}, 'largestQueueDepth':   0, 'largestQueueDepthTime': '1980-01-01 10:00:00.000000',},
    admins=['test_add_me_queue_at_max'],
    project=[('UNIT_TEST', 'BLAH')],
    queue=[{}] * QUEUE_THRESHOLD
)
def test_add_me_queue_at_max():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='Failed to add to queue because queue is already at maximum of "' + str(QUEUE_THRESHOLD) + '"',
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'add me'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot add person UNIT_TEST_PERSON",
      "personId": "test_add_person_queue_at_max",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id",
        "UNIT_TEST_PERSON_ID"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    global_stats={'historicalData':{'queues': {}, 'flush_times': {},
                                    'mostActiveQueueUsers': {}, 'quickestAtHeadUsers': {}, 'largestQueueDepths': {},
                                    'largestQueueDepthTimes': {}},
                  'maxQueueDepthByHour': {}, 'minQueueDepthByHour': {}, 'minFlushTimeByHour': {}, 'maxFlushTimeByHour': {}, 'largestQueueDepth':   0, 'largestQueueDepthTime': '1980-01-01 10:00:00.000000',},
    admins=['test_add_person_queue_at_max'],
    project=[('UNIT_TEST', 'BLAH')],
    queue=[{}] * QUEUE_THRESHOLD
)
def test_add_person_queue_at_max():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='Failed to add to queue because queue is already at maximum of "' + str(QUEUE_THRESHOLD) + '"',
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'add person UNIT_TEST_PERSON'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot create new project foobar",
      "personId": "test_create_new_project",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    admins=['test_create_new_project'],
    project=[('UNIT_TEST', 'BLAH')],
)
def test_create_new_project():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 2, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args_list[0] == \
           mock.call(
               markdown='Created new project \'FOOBAR\'.',
               roomId='BLAH',
           ), "Sent message not correct"
    assert CiscoSparkAPI().messages.create.call_args_list[1] == \
           mock.call(
               markdown='Registered bot to project \'FOOBAR\'',
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[7]
    assert tuple(['FOOBAR', 'BLAH']) in args[0]

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'create new project foobar'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot delete project",
      "personId": "test_delete_project",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    admins=['test_delete_project'],
    project=[('UNIT_TEST', 'BLAH')],
)
def test_delete_project():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='Successfully deleted project \'UNIT_TEST\'',
               roomId='BLAH',
           ), "Sent message not correct"


    args, kwargs = json.dump.call_args_list[3]
    assert [] == args[0]

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'delete project'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot list for all subprojects",
      "personId": "test_list_queue_all_subprojects",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    admins=['test_list_queue_all_subprojects'],
    project=[('UNIT_TEST', 'BLAH')],
)
def test_list_queue_all_subprojects_only_general():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='Current queue on subproject "GENERAL" is:\n\n'
                        'There is no one in the queue\n\nGiven that there are 0 people in the queue. '
                        'Estimated wait time from the back of the queue is:\n\n0:00:00',
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'list for all subprojects'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot list for all subprojects",
      "personId": "test_list_queue_all_subprojects_two_subprojects",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    subprojects=['GENERAL', 'OTHER_SUBPROJECT'],
    admins=['test_list_queue_all_subprojects_two_subprojects'],
    project=[('UNIT_TEST', 'BLAH')],
)
def test_list_queue_all_subprojects_two_subprojects():
    from endpoints import queue, CiscoSparkAPI
    queue()

    messages = [
        'Current queue on subproject "OTHER_SUBPROJECT" is:\n\n'
        'There is no one in the queue\n\nGiven that there are 0 people in the queue. '
        'Estimated wait time from the back of the queue is:\n\n0:00:00',

        'Current queue on subproject "GENERAL" is:\n\n'
        'There is no one in the queue\n\nGiven that there are 0 people in the queue. '
        'Estimated wait time from the back of the queue is:\n\n0:00:00'
    ]

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 2, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args_list[0][1]['markdown'] in messages, "Sent message not correct"
    assert CiscoSparkAPI().messages.create.call_args_list[1][1]['markdown'] in messages, "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'list for all subprojects'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show strict regex",
      "personId": "test_show_strict_regex_true",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    admins=['test_show_strict_regex_true'],
    project=[('UNIT_TEST', 'BLAH')],
    settings={
        'default_subproject': 'GENERAL',
        'strict_regex': True
    }
)
def test_show_strict_regex_true():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='Strict regex for project "UNIT_TEST" is: True',
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show strict regex'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show strict regex",
      "personId": "test_show_strict_regex_false",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    admins=['test_show_strict_regex_false'],
    project=[('UNIT_TEST', 'BLAH')],
    settings={
        'default_subproject': 'GENERAL',
        'strict_regex': False
    }
)
def test_show_strict_regex_false():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='Strict regex for project "UNIT_TEST" is: False',
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show strict regex'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot set strict regex to true",
      "personId": "test_set_strict_regex_to_true",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    admins=['test_set_strict_regex_to_true'],
    project=[('UNIT_TEST', 'BLAH')],
    settings={
        'default_subproject': 'GENERAL',
        'strict_regex': False
    }
)
def test_set_strict_regex_to_true():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='Strict regex for project "UNIT_TEST" is: True',
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'set strict regex to true'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot set strict regex to false",
      "personId": "test_set_strict_regex_to_false",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    admins=['test_set_strict_regex_to_false'],
    project=[('UNIT_TEST', 'BLAH')],
    settings={
        'default_subproject': 'GENERAL',
        'strict_regex': True
    }
)
def test_set_strict_regex_to_false():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='Strict regex for project "UNIT_TEST" is: False',
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'set strict regex to false'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot pun",
      "personId": "test_pun_easter_rejection",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    admins=['test_pun_easter_rejection'],
    project=[('UNIT_TEST', 'BLAH')],
    random=0.01
)
def test_pun_easter_rejection():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               files=['queuebot/rejection_pic.jpg'],
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'pun'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot cat fact",
      "personId": "test_cat_easter_rejection",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    admins=['test_cat_easter_rejection'],
    project=[('UNIT_TEST', 'BLAH')],
    random=0.01
)
def test_cat_easter_rejection():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               files=['queuebot/rejection_pic.jpg'],
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'cat fact'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot show admins",
      "personId": "test_admin_command_unregistered",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    admins=['test_admin_command_unregistered'],
    project=[],
)
def test_admin_command_unregistered():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='QueueBot is not registered to a project! Ask an admin to register this bot',
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'show admins'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot create new subproject foobar",
      "personId": "test_create_new_subproject",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    admins=['test_create_new_subproject'],
    project=[('UNIT_TEST', 'BLAH')],
)
def test_create_new_subproject():
    from endpoints import queue, CiscoSparkAPI
    import os
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 2, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args_list[0] == \
           mock.call(
               markdown='Successfully created new subproject "FOOBAR"',
               roomId='BLAH',
           ), "Sent message not correct"
    assert CiscoSparkAPI().messages.create.call_args_list[1] == \
           mock.call(
               markdown='Subprojects for project "UNIT_TEST" are:\n\n- GENERAL (DEFAULT)\n',
               roomId='BLAH',
           ), "Sent message not correct"

    assert 'queuebot/data/UNIT_TEST/FOOBAR' in [i[0][0] for i in os.makedirs.call_args_list]

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'create new subproject foobar'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot delete subproject foobar",
      "personId": "test_delete_subproject",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    admins=['test_delete_subproject'],
    project=[('UNIT_TEST', 'BLAH')],
    subprojects=['GENERAL', 'FOOBAR']
)
def test_delete_subproject():
    from endpoints import queue, CiscoSparkAPI
    import shutil
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 2, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args_list[0] == \
           mock.call(
               markdown='Successfully deleted subproject "FOOBAR"',
               roomId='BLAH',
           ), "Sent message not correct"
    assert CiscoSparkAPI().messages.create.call_args_list[1] == \
           mock.call(
               markdown='Subprojects for project "UNIT_TEST" are:\n\n- FOOBAR\n- GENERAL (DEFAULT)\n',
               roomId='BLAH',
           ), "Sent message not correct"

    assert 'queuebot/data/UNIT_TEST/FOOBAR' == shutil.rmtree.call_args[0][0]

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'delete subproject foobar'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot delete subproject general",
      "personId": "test_delete_subproject",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    admins=['test_delete_subproject'],
    project=[('UNIT_TEST', 'BLAH')],
    subprojects=['GENERAL', 'FOOBAR']
)
def test_delete_default_subproject():
    from endpoints import queue, CiscoSparkAPI
    import shutil
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='You cannot delete the default subproject.',
               roomId='BLAH',
           ), "Sent message not correct"

    assert not shutil.rmtree.called

    args, kwargs = json.dump.call_args_list[1]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'delete subproject general'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot change default subproject to general",
      "personId": "test_set_default_to_already_set",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    admins=['test_set_default_to_already_set'],
    project=[('UNIT_TEST', 'BLAH')],
    subprojects=['GENERAL', 'FOOBAR']
)
def test_set_default_to_already_set():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='Default subproject is already set to "GENERAL"',
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'change default subproject to general'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot change default subproject to foobar",
      "personId": "test_change_default_subproject_valid",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    admins=['test_change_default_subproject_valid'],
    project=[('UNIT_TEST', 'BLAH')],
    subprojects=['GENERAL', 'FOOBAR']
)
def test_change_default_subproject_valid():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 2, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args_list[0] == \
           mock.call(
               markdown='Default subproject changed to "FOOBAR"',
               roomId='BLAH',
           ), "Sent message not correct"
    assert CiscoSparkAPI().messages.create.call_args_list[1] == \
           mock.call(
               markdown='Subprojects for project "UNIT_TEST" are:\n\n- FOOBAR (DEFAULT)\n- GENERAL\n',
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[3]
    assert args[0]['default_subproject'] == 'FOOBAR'

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'change default subproject to foobar'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot change default subproject to invalid",
      "personId": "test_change_default_subproject_invalid",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    admins=['test_change_default_subproject_invalid'],
    project=[('UNIT_TEST', 'BLAH')],
    subprojects=['GENERAL', 'FOOBAR']
)
def test_change_default_subproject_invalid():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='Subproject "INVALID" does not exist on project "UNIT_TEST"',
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'change default subproject to invalid'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot register bot to project valid",
      "personId": "test_register_bot_to_valid_project",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    admins=['test_register_bot_to_valid_project'],
    project=[('UNIT_TEST', 'BLAH'), ('VALID', 'OTHERROOM')],
    subprojects=['GENERAL', 'FOOBAR']
)
def test_register_bot_to_valid_project():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='Successfully registered bot to project "VALID"',
               roomId='BLAH',
           ), "Sent message not correct"

    assert ('VALID', 'BLAH') in json.dump.call_args_list[3][0][0]

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'register bot to project valid'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot register bot to project valid",
      "personId": "test_register_bot_to_valid_project_not_admin",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    project=[('VALID', 'OTHERROOM')]
)
def test_register_bot_to_valid_project_not_admin():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='ERROR: You are not registered as an admin on project "VALID"',
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'register bot to project valid'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot register bot to project unit_test",
      "personId": "test_register_bot_already_registered",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    admins=['test_register_bot_already_registered'],
    project=[('UNIT_TEST', 'BLAH')],
    subprojects=['GENERAL', 'FOOBAR']
)
def test_register_bot_already_registered():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='This bot is already registered to project \'UNIT_TEST\'',
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'register bot to project unit_test'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot delete project",
      "personId": "test_delete_project_unregistered",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    admins=['test_delete_project_unregistered'],
    project=[('UNIT_TEST', 'OTHERROOM')]
)
def test_delete_project_unregistered():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='QueueBot is not registered to a project! Ask an admin to register this bot',
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'delete project'


@freeze_time("1980-01-01 12:00:00.000000")
@with_request(data={
      "id": "message-id",
      "roomId": "BLAH",
      "roomType": "group",
      "text": "QueueBot create new project UNIT_TEST",
      "personId": "test_create_project_already_exists",
      "personEmail": "avthorn@cisco.com",
      "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"me_id\">QueueBot</spark-mention> list</p>",
      "mentionedPeople": [
        "me_id"
      ],
      "created": "2018-04-02T14:23:08.086Z"
    },
    admins=['test_create_project_already_exists'],
    project=[('UNIT_TEST', 'OTHERROOM')]
)
def test_create_project_already_exists():
    from endpoints import queue, CiscoSparkAPI
    queue()

    assert len(CiscoSparkAPI().messages.create.call_args_list) == 1, "Too many messages sent"
    assert CiscoSparkAPI().messages.create.call_args == \
           mock.call(
               markdown='ERROR: project \'UNIT_TEST\' already exists.',
               roomId='BLAH',
           ), "Sent message not correct"

    args, kwargs = json.dump.call_args_list[2]
    assert args[0][-1]['sparkId'] == 'message-id' and args[0][-1]['command'] == 'create new project UNIT_TEST'