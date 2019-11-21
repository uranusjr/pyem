==================================================
PyEM: Project-level virtual environment management
==================================================

PyEM manages multiple virtual environments local to projects. It provides
shortcuts to create, remove, switch between, and run commands against virtual
environments created against various Python interpreters.


In Action
=========

Add a virtual environment::

    $ pyem venv add python3.7  # Based on a command.

    $ pyem venv add 3.6  # Based on interpreter found by the Python launcher.

    $ pyem venv add /usr/local/bin/pypy3  # Based on an executable.

The second variant relies on the `Python launcher`_ to locate an interpreter.
This tool should be installed by default if you use the officlal installer on
Windows (and do not explicitly choose not to install it). For other platforms,
`Python launcher for UNIX`_ by Brett Cannon can be used as an alternative.

.. _`Python launcher`: https://docs.python.org/3/using/windows.html#launcher
.. _`Python launcher for UNIX`: https://github.com/brettcannon/python-launcher


List managed virtual environments::

    $ pyem venv list
      Quintuplet
    =============================================
      cpython-3.6-darwin-x86_64-f14a3513
      cpython-3.7-darwin-x86_64-dbe83ac5
    * pypy-3.6-darwin-x86_64-dc1298a1


Set active virtual environment::

    $ pyem venv set 3.7
    Switched to cpython-3.7-darwin-x86_64-dbe83ac5

    $ pyem venv set 3.6
    Error: name '3.6' is ambiguous; choose from:
      cpython-3.6-darwin-x86_64-f14a3513
      pypy-3.6-darwin-x86_64-dc1298a1

    $ pyem venv set cpython-3.6
    Switched to cpython-3.6-darwin-x86_64-f14a3513


Run a command inside a virtual environment::

    $ pyem poetry run python -c "import sys; print(sys.executable)"
    /tmp/exampleproject/.venvs/bin/python

    $ pyem --spec=pypy-3.6 pipenv run pypy3 -c "import sys; print(sys.executable)"
    /tmp/exampleproject/.venvs/bin/pypy3


How does this work?
===================

PyEM sets environment variables ``VIRTUAL_ENV`` and ``PATH``, and hand off
control to ``subprocess`` for the command specified. This is enough to trick
a lot of Python project tools, including the `Python launcher`_, Poetry_, and
Pipenv_.

.. _Poetry: https://poetry.eustace.io
.. _Pipenv: https://github.com/pypa/pipenv

Flit is more difficult to trick since it does not automatically inspect
environment variables like other tools do. Use this workaround instead::

    $ pyem flit install --python=python
