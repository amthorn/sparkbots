import flask
import ciscosparkapi

from queuebot.decorators import with_request
from unittest import mock
from contextlib import contextmanager


def test_empty_data():
    with mock.patch("flask.request") as mock_api:
        flask.request.json={}
        with mock.patch("ciscosparkapi.CiscoSparkAPI") as mock_api:
            from endpoints import queue
            queue()


@with_request(dict(mentionedPeople={1}))
def test_early_exception():
    from endpoints import CiscoSparkAPI, queue
    og = CiscoSparkAPI.return_value
    CiscoSparkAPI.return_value = None
    queue()
    CiscoSparkAPI.return_value = og


@with_request({
  "id": "Y2lzY29zcGFyazovL3VzL01FU1NBR0UvNWQ2YzRkNjAtMzY4MS0xMWU4LWE1MjItNDUxOGNlZjI0ODQ5",
  "roomId": "BLAH",
  "roomType": "group",
  "text": "QueueBot list",
  "personId": "Y2lzY29zcGFyazovL3VzL1BFT1BMRS9kODRkZjI1MS1iYmY3LTRlZTEtOTM1OS00Y2I0MGIyOTBhN2I",
  "personEmail": "avthorn@cisco.com",
  "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"Y2lzY29zcGFyazovL3VzL1BFT1BMRS9hYzIzODBlNi02MGFmLTQyZGYtYjQxZS0zNjM1NWM3N2IzZDM\">QueueBot</spark-mention> list</p>",
  "mentionedPeople": [
    "Y2lzY29zcGFyazovL3VzL1BFT1BMRS9hYzIzODBlNi02MGFmLTQyZGYtYjQxZS0zNjM1NWM3N2IzZDM"
  ],
  "created": "2018-04-02T14:23:08.086Z"
})
def test_queue_list():
    from endpoints import queue, CiscoSparkAPI
    queue()
    assert CiscoSparkAPI().messages.create.call_count == 1


# @with_request(data={
#   "id": "Y2lzY29zcGFyazovL3VzL01FU1NBR0UvNWQ2YzRkNjAtMzY4MS0xMWU4LWE1MjItNDUxOGNlZjI0ODQ5",
#   "roomId": "BLAH",
#   "roomType": "group",
#   "text": "QueueBot add me",
#   "personId": "Y2lzY29zcGFyazovL3VzL1BFT1BMRS9kODRkZjI1MS1iYmY3LTRlZTEtOTM1OS00Y2I0MGIyOTBhN2I",
#   "personEmail": "avthorn@cisco.com",
#   "html": "<p><spark-mention data-object-type=\"person\" data-object-id=\"Y2lzY29zcGFyazovL3VzL1BFT1BMRS9hYzIzODBlNi02MGFmLTQyZGYtYjQxZS0zNjM1NWM3N2IzZDM\">QueueBot</spark-mention> list</p>",
#   "mentionedPeople": [
#     "Y2lzY29zcGFyazovL3VzL1BFT1BMRS9hYzIzODBlNi02MGFmLTQyZGYtYjQxZS0zNjM1NWM3N2IzZDM"
#   ],
#   "created": "2018-04-02T14:23:08.086Z"
# },
# people=[
#     {
#
#     }
# ])
# def test_add_me():
#     from endpoints import queue, CiscoSparkAPI
#     queue()
#     import pdb; pdb.set_trace()

