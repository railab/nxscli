## Contributing to Nxscli

### Recommended tools

We use [tox](https://github.com/tox-dev/tox) to automate tedious developer's tasks, 
thus installing it is highly recommended.

```
pip install --user tox
```

### Setting up for development

1. Clone the _Nxscli_ repository.

```
git clone https://github.com/railab/nxscli.git
cd nxscli
```

2. Create and activate a virtual environment

```
virtualenv venv
source venv/bin/activate
```

3. Install the project in editable mode

`pip install -e .`

### Code style and running tests

Code formatting is ensured by [black](https://github.com/psf/black) and [isort](https://github.com/PyCQA/isort).
To reformat your changes, use:

```
tox -e format
```

Untyped function definitions are disallowed (`mypy --disallow-untyped-defs`).
Type checking can be run with:

```
tox -e type
```

Flake8 linter is available with:

```
tox -e flake8
```

CI requres 100% coverage to pass. If some of your changes can't be easy tested, 
you can exclude code from coverage with `#pragma: no cover` comment.
To run tests with coverage report run:

```
tox -e py
```

If you don't care about coverage report or want to run tests in parallel, just use:

```
tox -e test
```

Current the pylint report isn't taken into account to pass CI (in the future
it may change), but it's available from tox:

```
tox -e pylint
```

### CI

Please run `tox` before submitting a patch to be sure your changes will pass CI.

The Windows tests are known to occasionally fail.
