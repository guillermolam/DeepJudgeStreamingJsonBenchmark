# DeepJudge.ai

Thank you for your interest in our software engineering position - we are excited to see what you can do!
We would like to ask you to complete a small coding task as part of our interview process.
This task should take you around an hour to complete.
The task description is as follows:

## Develop a Streaming JSON Parser

### Objective:

You are required to implement a streaming JSON parser that processes JSON data incrementally in Python.
The primary motivation for this task is to simulate partial responses as would be encountered in the streaming output of
a large language model (LLM).

### Preconditions:

1. You can use whatever tools you want (Debugger, Editor, Copilot, ChatGPT, …).
2. For this task, we consider a subset of JSON:
    - Values consist solely of strings and objects.
    - Escape sequences in strings or duplicate keys in objects are not expected.

### Requirements:

### Requirements:

1. Create a class named `StreamingJsonParser`.
    2. Implement the following methods within this class:
        1. `__init__()`: Initializes the parser.
        2. `consume(buffer: str)`: Consumes a chunk of JSON data.
        3. `get()`: Returns the current state of the parsed JSON object as an appropriate Python object.
        4. Even if the input JSON data is incomplete, the parser should be able to return the current state of the
           parsed
           JSON object at any given point in time.
    5. This should include partial string-values and objects, but not the keys themselves,
    6. i.e. `{"test": "hello", "worl` is a partial representation of `{"test": "hello"}`,
    7. `{"test": "hello", "worl": ""}` is not a valid representation of `{"test": "hello"}`
    8. The parser should be able to handle partial keys and partial string values.Partial Keys should NOT be returned.
    9. Only once the value type of the key is determined should the parser return the key-value pair.
    10. Partial String values on the other hand can be partially returned: `{"test": "hello", "country": "Switzerl` is a
        partial representation of `{"test": "hello", "country": "Switzerl"}`.
    11. The parser should be efficient in terms of algorithmic complexity.

3. You may create a test function named `test_streaming_json_parser()` to verify the correctness of your implementation.
4. You may create additional helper classes or functions as needed.
5. Ensure that your code is well-documented and follows best practices for Python coding.
6. Include a docstring in your class and methods to explain the purpose and usage of each method.
7. Include a check function named `check_solution()` to verify the correctness of your solution against provided test
   cases.
    8. These are examples of made up test but that showcase how Parsers will be used to check your solution.
       #### Examples:

        ```python
        def test_streaming_json_parser():
         parser = StreamingJsonParser()
         parser.consume('{"foo": "bar"}')
         assert parser.get() == {"foo": "bar"}
     
        def test_chunked_streaming_json_parser():
         parser = StreamingJsonParser()
         parser.consume('{"foo":')
         parser.consume('"bar')
         assert parser.get() == {"foo": "bar"}
     
        def test_partial_streaming_json_parser():
         parser = StreamingJsonParser()
         parser.consume('{"foo": "bar')
         assert parser.get() == {"foo": "bar"}
        ```

Once you're done, send us a python file with your solution as a response to this E-Mail.

> IMPORTANT: If you want your submission to be considered, please hand it in as a **single** python file called
`guillermo_lam_streaming_json_parser.py`. Submissions that do not follow this pattern will not be considered.

Thank you and good luck!
