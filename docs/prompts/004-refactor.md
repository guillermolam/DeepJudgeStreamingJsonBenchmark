## 🧠 LLM Task Prompt: Streaming JSON Parser Refactor

### 🔧 ROLE

You are a **Python serialization and streaming architecture expert**.

### 🧠 OBJECTIVE

For each parser module in this project, refactor the `StreamingJsonParser` class to strictly support **byte-based input
** and correct the following error:

```bash
TypeError: can
TypeError: can only concatenate str (not "bytes") to str
```

This issue occurs due to improper handling or mixing of str and bytes types. Your goal is to eliminate this error across
all parser implementations by:

### PARSER FILES LOCATIONS

- `/src/serializers/anyio/*.py`
- `/src/serializers/raw/*.py`
- `/src/serializers/solid/*.py`


## DO NOT USE
```python
import json
```

### ✅ TASK CHECKLIST

#### 1. Type Safety and Encoding

- Refactor the `consume()` method to accept and operate exclusively on `bytes`.
- Use `.decode("utf-8")` explicitly when converting bytes to strings.
- Ensure the class never mixes `str` with `bytes` internally.

#### 2. Assignment Specification Compliance

Refactor the class to satisfy all requirements from the assignment:

```bash
class StreamingJsonParser:
    def __init__(self): ...
    def consume(self, buffer: str): ...
    def get(self) -> dict: ...
```

##### The parser must:

- Return a correct partial JSON object at any time.
- Exclude incomplete keys.
- Support partially completed string values.
- Be efficient in time and space complexity as much as possible, as this is a competition. best (performance and clean
  code) algorithm submission
  gets the job
- Fail gracefully without raising on incomplete input.

### 🧪 MANDATORY TESTS TO INCLUDE (AT END OF EACH FILE)

Include and pass the following tests in each parser module:
Refactor the consume() method to accept and operate exclusively on bytes.

Use .decode("utf-8") explicitly when converting bytes to strings.

Ensure the class never mixes str with bytes internally.

2. Assignment Specification Compliance
   Refactor the class to satisfy all requirements from the assignment:

```python
class StreamingJsonParser:

    def __init__(self): ...


def consume(self, buffer: str): ...


def get(self) -> dict: ...
```

##### The parser must:

- Return a correct partial JSON object at any time.
- Exclude incomplete keys.
- Support partially completed string values.
- Maximize efficiency in time and space complexity.
- Fail gracefully without raising on incomplete input.

### 🧪 MANDATORY TESTS TO INCLUDE (AT END OF EACH FILE)

Include and pass the following tests in each parser module:

```python

def test_streaming_json_parser():


parser = StreamingJsonParser()
parser.consume(b'{"foo": "bar"}')
assert parser.get() == {"foo": "bar"}


def test_chunked_streaming_json_parser():


parser = StreamingJsonParser()
parser.consume(b'{"foo": ')
parser.consume(b'"bar"}')
assert parser.get() == {"foo": "bar"}


def test_partial_streaming_json_parser():


parser = StreamingJsonParser()
parser.consume(b'{"foo": "bar')
assert parser.get() == {"foo": "bar"}
```

### 📌 CODE QUALITY REQUIREMENTS

- Use clear variable names and modular helper functions.
- Follow Pythonic idioms and PEP8 standards.
- Add meaningful docstrings for every method and class.
- Ensure deterministic behavior and reproducibility.
- Favor readability, testability, and low complexity.
- Your final code should be robust, clean, safe for production, and aligned with best practices in streaming parser
  design.
- SOLID principles are a must but not at expense of performance.
- Clean code is a must but not at expense of performance.
- Encapsulate if/else logic in helper functions with meaningful names.
- Use clear variable names and modular helper functions.
- Follow Pythonic idioms and PEP8 standards.
- Add meaningful docstrings for every method and class.
- Ensure deterministic behavior and reproducibility.
- Favor readability, testability, and low complexity.
- Your final code should be robust, clean, safe for production, and aligned with best practices in streaming parser
  design.
- Your final code should follow SOLID principles are a must but not at expense of performance or lapse time.
- Your final code should be robust, clean, safe for production, and aligned with best practices in streaming parser
  design.
- Clean code is a must but not at expense of performance.
- Encapsulate if/else logic in helper functions with meaningful names.

### GITHUB REMOTE REPOSITORY

- Use this Github repo: https://github.com/guillermolam/DeepJudgeStreamingJsonBenchmark
- use master branch
