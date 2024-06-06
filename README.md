BigBlueButton Presentation Area Video Generator
===============================================

This is a tool that is part of the BigBlueButton recording processing system,
used to generate a video file of just the presentation area, with slides and
annotations included, from the recording events file and archived presentation
pdf files.

The current version is work in process adding support for the tldraw
whiteboard introduced in BigBlueButton 2.6.

Development Environment Notes
-----------------------------

Several libraries are used via the gobject-introspection based bindings.
The corresponding ubuntu packages to get these bindings are:
  - gir1.2-glib-2.0
  - gir1.2-poppler-0.18
  - gir1.2-gtk-3.0
  - gir1.2-gdkpixbuf-2.0
  - gir1.2-pango-1.0

You'll need ffmpeg for the video encoding to operate correctly. The version
included with the current BigBlueButton release is sufficient.

You will also need the Microsoft core fonts installed (or something
metric-compatible with appropriate aliases enabled like fonts-croscore), since
the text annotations require Arial.

For development, I recommend using a python venv. Set this up with a command
like:

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip --require-virtualenv --upgrade pip
```

Any time you open a new terminal, you can re-run the `source` command to load
it again later.

With the venv activated, you can use `pip` to install the required python
modules and development tools:

```sh
pip install --require-virtualenv --upgrade -r requirements-dev.txt -c constraints-ubuntu-jammy.txt
```

(You should re-run this occasionally to pull in updates to the development tools.)

Testing
-------

`bbb-presentation-video` does not currently have any test suite to run, but
we do enforce typing correctness using
[mypy](https://mypy.readthedocs.io/en/stable/).

To run the type checking, run `mypy` in the root of the project checkout with
no additional options.

Configuration is loaded from `pyproject.toml`. Type stubs for some third party
libraries that do not provide type information is located in the `typings`
directory.

Code Style
----------

Standard code style is enforced using
[black](https://black.readthedocs.io/en/stable/) with default options. You can
run `black .` in the root of the project to correct all files, or run `black`
on a specific file.

Additionally, sorting of import directives is done using
[isort](https://pycqa.github.io/isort/) using the black-compatible profile.
You can run `isort .` in the root of the project to correct all files, or run
`isort` on a specific file.

Note that you may need to run black after running isort to correct minor style
issues that isort sometimes introduces.
