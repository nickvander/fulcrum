# Fulcrum Documentation Source

This directory contains the source files and configuration for the Fulcrum
project's official technical documentation.

The content of the documentation can be found in the `docs/source/` directory.

## Contributing to the Documentation

We welcome contributions to improve the documentation.

### Tech Stack

The documentation is built using [Sphinx](https://www.sphinx-doc.org/), a
powerful documentation generator, and written in Markdown using the
[MyST parser](https://myst-parser.readthedocs.io/).

### Local Development & Preview

To work on the documentation locally, you must first set up a local Python
development environment. Please follow the **[Contributor Guide](../../CONTRIBUTING.md)**
to install `uv` and create a virtual environment.

Once your environment is set up, you can run a live-reloading web server from
the project root:

```bash
npm run docs:serve
```
