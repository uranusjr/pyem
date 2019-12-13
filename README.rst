==================================================
PyEM: Project-level virtual environment management
==================================================

PyEM manages multiple virtual environments local to projects. It provides
shortcuts to create, remove, switch between, and run commands against virtual
environments created against various Python interpreters.


Install
=======

I recommend using pipx_::

    pipx install pyem

    # If you need to support Python without the builtin venv module.
    pipx inject pyem virtualenv

.. _pipx: https://pipxproject.github.io/pipx/


In Action
=========

Add a virtual environment besides the file ``pyproject.toml``::

    # Based on a command.
    pyem venv add python3.7

    # Based on interpreter found by the Python launcher.
    pyem venv add 3.6

    # Based on an executable.
    pyem venv add /usr/local/bin/pypy3

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


Tips and Tricks
===============

Flit on Windows
---------------

Flit_ has problems detecting the active virtual environment on Windows when
installed into Python 3.7.2 or later. Use the following workaround (requires
the Python launcher)::

    $ pyem flit install --python=py

.. _Flit: https://github.com/takluyver/flit

Starting from Flit 2.1, you can also set the environment variable
``FLIT_INSTALL_PYTHON=py`` for the same effect. This is a good default even
when you're not using PyEM IMO; it makes more sense than installing into Flit's
environment.

This has been fixed in master (`takluyver/flit#300`_), so Flit *after* 2.1.0
does not need this workaround.

.. _`takluyver/flit#300`: https://github.com/takluyver/flit/pull/300


Project without ``pyproject.toml``
----------------------------------

If your project does not use ``pyproject.toml``, you can specify the project
root explicitly::

    pyem --project=./myproject add 3.8

The ``--project`` option is only required when creating a virtual environment.
Subsequent commands should pick up the ``.venvs`` directory automatically, and
use its location as the project root, even without the presence of
``pyproject.toml``.


Call a virtual environment outside the project root
---------------------------------------------------

The ``--project`` option is also handy if you want to access a virtual
environment when you're outside of the project root. This command lists
installed packages in the 3.7 virtual environment of ``another-project``::

    pyem --project=../another-project --python=3.7 pip list
