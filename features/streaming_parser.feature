Feature: Streaming JSON Parser
  As a developer, I want to use a streaming JSON parser
  that can handle partial and complete JSON objects,
  so that I can process JSON data incrementally.

  Scenario: Parse a complete JSON object
    Given a StreamingJsonParser instance
    When I consume the chunk '{"foo": "bar"}'
    Then the result should be {"foo": "bar"}

  Scenario: Parse a chunked JSON object
    Given a StreamingJsonParser instance
    When I consume the chunk '{"foo": '
    And I consume the chunk '"bar"}'
    Then the result should be {"foo": "bar"}

  Scenario: Parse a partial string value
    Given a StreamingJsonParser instance
    When I consume the chunk '{"hello": "worl'
    Then the result should be {"hello": "worl"}

  Scenario: Do not return partial keys
    Given a StreamingJsonParser instance
    When I consume the chunk '{"par'
    Then the result should be {}

  Scenario: Parse multiple key-value pairs with the last one being partial
    Given a StreamingJsonParser instance
    When I consume the chunk '{"a": "1", "b": 2'
    Then the result should contain {"a": "1"}
    And if "b" is in the result, it should be 2

  Scenario: Parse boolean and null values
    Given a StreamingJsonParser instance
    When I consume the chunk '{"t": true, "f": false, "n": null'
    Then the result should contain {"t": true, "f": false, "n": null}

  Scenario: Parse a complete nested object
    Given a StreamingJsonParser instance
    When I consume the chunk '{"outer": {"inner": "value"}}'
    Then the result should be {"outer": {"inner": "value"}}

  Scenario: Parse a partial nested object
    Given a StreamingJsonParser instance
    When I consume the chunk '{"outer": {"inner": "val'
    Then the result should contain {"outer": {"inner": "val"}}
