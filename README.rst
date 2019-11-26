==================================================
PyEM: Project-level virtual environment management
==================================================

PyEM manages multiple virtual environments local to projects. It provides
shortcuts to create, remove, switch between, and run commands against virtual
environments created against various Python interpreters.


Install
=======

I recommend using pipx_::

  pipx install pyem --spec="pyem[compat]"

The "compat" extra also installs virtualenv_ to support old Python versions
without the builtin ``venv`` module. You can drop it if you don't need this.
(You can always ``pipx inject`` virtualenv back if you need to.)

.. _pipx: https://pipxproject.github.io/pipx/
.. _virtualenv: https://virtualenv.pypa.io/en/stable/


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
a lot of Python project tools, including the Python launcher, Poetry_, and
Pipenv_. Python interpreters with ``venv`` support (e.g. CPython 3.3 or later)
should also integrate seamlessly.

.. _Poetry: https://poetry.eustace.io
.. _Pipenv: https://github.com/pypa/pipenv

Flit_ is more difficult to trick since it does not automatically inspect
environment variables like other tools do. Use this workaround instead
(requires the Python launcher)::

    $ pyem flit install --python=py

.. _Flit: https://github.com/takluyver/flit

Starting from Flit 2.1, you can also set the environment variable
``FLIT_INSTALL_PYTHON=py`` for the same effect. This is a good default even
when you're not using PyEM IMO; it makes more sense than installing into Flit's
environment.
