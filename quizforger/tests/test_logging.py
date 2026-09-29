import json
import logging

from django.test import SimpleTestCase

from config.logging import JsonFormatter


class JsonFormatterTests(SimpleTestCase):
    def test_request_objects_and_unknown_fields_are_not_serialized(self):
        record = logging.LogRecord(
            name="django.request",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="request failed",
            args=(),
            exc_info=None,
        )
        record.request = object()
        record.query_string = "token=must-not-appear"
        record.status_code = 500
        record.event = "request_failed"

        payload = json.loads(JsonFormatter().format(record))

        self.assertNotIn("request", payload)
        self.assertNotIn("query_string", payload)
        self.assertNotIn("must-not-appear", json.dumps(payload))
        self.assertEqual(payload["status_code"], 500)
        self.assertEqual(payload["event"], "request_failed")
