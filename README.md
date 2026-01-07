
# pySOF0273

## Description
CLI tool to configure attenuation of DOS0157 racks from [AMG Microwave](www.amg-microwave.com)


## Installation

Recommended installation (inside a virtual environment):

- Install the package and its runtime dependencies:

```bash
python -m pip install .
```

- To also install development dependencies (tests, linters):

```bash
python -m pip install .[dev]
```

- To work in editable/development mode:

```bash
python -m pip install -e .[dev]
```

After installation, the `sof0273` console script is available in your `PATH` (activate your venv if necessary):

```bash
sof0273 -h
```


## Usage

```bash
$ sof0273 
Connected to /dev/ttyUSB0 at 9600 baud. Parity=N Stopbits=1.0
Enter commands to send to the device.Commands:
  r                           - Read current attenuation settings
  w <Att_LOFAR> <Att_NenuFAR> - Set attenuation in dB (0.0 to 31.5)
  s                           - Save current settings to device memory

Type 'quit' to exit.

> 
```


## CI and running tests locally

We provide a simple Makefile to run the test suite locally or in CI.

Project layout

- Source files live in `src/` (add `src/` to `PYTHONPATH` when running Python tools).
- Executable wrapper `scripts/sof0273` runs the CLI (sets `PYTHONPATH` to include `src/`).

Use the Makefile targets:

- `make install` — install test dependencies into a local virtualenv `.venv` (or fallback to `./.local_packages`).
- `make test` — run the test suite.
- `make ci` — runs tests and writes a JUnit XML report to `report.xml` (used by GitLab CI).

On GitLab, the pipeline runs `make ci` and collects `report.xml` as the JUnit report.

Pre-commit hooks

We use `pre-commit` to run fast linters and also to run the test suite on commits. To set it up locally:

```bash
# install the tool (preferably in your venv)
python3 -m pip install --user pre-commit
# install the git hooks in .git/hooks/pre-commit
pre-commit install
# run all hooks on all files (useful right after adding the config)
pre-commit run --all-files
```

There are Makefile helpers:

- `make precommit-install` — install `pre-commit` and register git hooks
- `make precommit-run` — run the hooks on all files locally

The GitLab pipeline also runs `pre-commit` in its own job before running the tests.


## CI, Runners and pipelines

A GitLab Runner is required to pick up and execute CI/CD jobs after commits.

Once installed with `gitlab-runner register ....`, start local instance with `gitlab-runner run`.

***

