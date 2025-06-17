from pytest_bdd import scenarios, given, when, then, parsers
import json
from src.serializers.solid.ultrajson_parser import StreamingJsonParser

scenarios('../streaming_parser.feature')

@given('a StreamingJsonParser instance', target_fixture='parser')
def parser():
    return StreamingJsonParser()

@when(parsers.parse("I consume the chunk '{chunk}'"))
def consume_chunk(parser, chunk):
    parser.consume(chunk)

@then(parsers.parse('the result should be {expected_result}'))
def result_should_be(parser, expected_result):
    expected = json.loads(expected_result)
    assert parser.get() == expected

@then(parsers.parse('the result should contain {expected_result}'))
def result_should_contain(parser, expected_result):
    expected = json.loads(expected_result)
    actual = parser.get()
    for key, value in expected.items():
        assert key in actual
        assert actual[key] == value

@then(parsers.parse('if "{key}" is in the result, it should be {value:d}'))
def if_key_in_result(parser, key, value):
    actual = parser.get()
    if key in actual:
        assert actual[key] == value
