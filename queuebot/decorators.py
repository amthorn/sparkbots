import ciscosparkapi
import flask
from functools import wraps, partial
from unittest import mock

ME_ID = 'Y2lzY29zcGFyazovL3VzL1BFT1BMRS9hYzIzODBlNi02MGFmLTQyZGYtYjQxZS0zNjM1NWM3N2IzZDM'


def with_request(data):
    def with_request_dec(func, *args, **kwargs):
        @wraps(func)
        def closure(*args, **kwargs):
            with mock.patch("flask.request") as mock_api:
                flask.request.json={'data': data}
                with mock.patch("endpoints.CiscoSparkAPI") as mock_api:
                    mock2 = mock.MagicMock()
                    mock2.id = ME_ID
                    mock2.displayName = 'QueueBot'

                    mock1 = mock.MagicMock()
                    mock1.people.me.return_value = mock2

                    # mock message id
                    message_mock = mock.MagicMock()
                    message_mock.id = data.get('id')
                    message_mock.personId = data.get('personId')
                    message_mock.roomId = data.get('roomId')
                    message_mock.text = data.get('text')
                    mock1.messages.get.return_value = message_mock

                    mock_api.return_value = mock1

                    return func(*args, **kwargs)
        return closure

    return with_request_dec
