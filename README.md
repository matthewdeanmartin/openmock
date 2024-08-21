# Openmock

Mock/fake of opensearch library, allows you to mock opensearch-py

Fork of Python Elasticsearch(TM) Mock. Sometimes the developers who work with elasticsearch (TM),
don't really have any input in choice of host and need to get work done.

![Libraries.io dependency status for latest release](https://img.shields.io/librariesio/release/pypi/openmock) [![Downloads](https://pepy.tech/badge/openmock/month)](https://pepy.tech/project/openmock/month)

## Installation

```shell
pip install openmock
```

## Usage

To use Openmock, decorate your test method with **@openmock** decorator:

```python
from unittest import TestCase

from openmock import openmock


class TestClass(TestCase):

    @openmock
    def test_should_return_something_from_opensearch(self):
        self.assertIsNotNone(some_function_that_uses_opensearch())
```

### Custom Behaviours

You can also force the behaviour of the OpenSearch instance by importing the `openmock.behaviour` module:

```python
from unittest import TestCase

from openmock import behaviour


class TestClass(TestCase):

    ...

    def test_should_return_internal_server_error_when_simulate_server_error_is_true(self):
        behaviour.server_failure.enable()
        ...
        behaviour.server_failure.disable()
```

You can also disable all behaviours by calling `behaviour.disable_all()` (Consider put this in your `def tearDown(self)` method)

#### Available Behaviours

- `server_failure`: Will make all calls to OpenSearch returns the following error message:
  ```python
  {
      'status_code': 500,
      'error': 'Internal Server Error'
  }
  ```

## Code example

Let's say you have a prod code snippet like this one:

```python
import opensearchpy

class FooService:

    def __init__(self):
        self.es = opensearchpy.OpenSearch(hosts=[{'host': 'localhost', 'port': 9200}])

    def create(self, index, body):
        es_object = self.es.index(index, body)
        return es_object.get('_id')

    def read(self, index, id):
        es_object = self.es.get(index, id)
        return es_object.get('_source')

```

Then you should be able to test this class by mocking OpenSearch using the following test class:

```python
from unittest import TestCase
from openmock import openmock
from foo.bar import FooService

class FooServiceTest(TestCase):

    @openmock
    def should_create_and_read_object(self):
        # Variables used to test
        index = 'test-index'
        expected_document = {
            'foo': 'bar'
        }

        # Instantiate service
        service = FooService()

        # Index document on OpenSearch
        id = service.create(index, expected_document)
        self.assertIsNotNone(id)

        # Retrieve document from OpenSearch
        document = service.read(index, id)
        self.assertEquals(expected_document, document)

```

## Notes:

- The mocked **search** method returns **all available documents** indexed on the index with the requested document type.
- The mocked **suggest** method returns the exactly suggestions dictionary passed as body serialized in OpenSearch.suggest response. **Attention:** If the term is an *int*, the suggestion will be `python term + 1`. If not, the suggestion will be formatted as `python {0}_suggestion.format(term) `.
  Example:
  - **Suggestion Body**:
  ```python
  suggestion_body = {
      'suggestion-string': {
          'text': 'test_text',
          'term': {
              'field': 'string'
          }
      },
      'suggestion-id': {
          'text': 1234567,
          'term': {
              'field': 'id'
          }
      }
  }
  ```
  - **Suggestion Response**:
  ```python
  {
      'suggestion-string': [
          {
              'text': 'test_text',
              'length': 1,
              'options': [
                  {
                      'text': 'test_text_suggestion',
                      'freq': 1,
                      'score': 1.0
                  }
              ],
              'offset': 0
          }
      ],
      'suggestion-id': [
          {
              'text': 1234567,
              'length': 1,
              'options': [
                  {
                      'text': 1234568,
                      'freq': 1,
                      'score': 1.0
                  }
              ],
              'offset': 0
          }
      ],
  }
  ```

## Testing

Preferred for testing one version of python.

```bash
pytest test
```

Won't catch pytest tests.

```bash
python -m unittest
```

We are trying to support a full matrix of openmock versions and python versions 3.9+. This is slow.

```bash
tox
```

## Changelog

See [CHANGELOG.md](https://github.com/matthewdeanmartin/openmock/blob/main/CHANGELOG.md)

## License

MIT with `normalize_host.py` being Apache 2 from Elasticsearch.
