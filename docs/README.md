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

### Theming

The documentation uses the modern [Furo](https://pradyunsg.me/furo/) theme.

All theme customizations, including the color palettes for both light and dark
mode, are configured directly in the `docs/source/conf.py` file within the
`html_theme_options` dictionary. This provides a single, centralized place to
manage the look and feel of the documentation site.

### Local Development & Preview

To work on the documentation locally, you must first set up a local Python
development environment. Please follow the **[Contributor Guide](../CONTRIBUTING.md)**
to install `uv` and create a virtual environment.

Once your environment is set up, you can run a live-reloading web server from
the project root:

```bash
npm run docs:serve
```

### Static Site Generation

To build a static version of the documentation (e.g., for deployment), run the
following command from the project root:

```bash
npm run docs:build
```

The static HTML files will be generated in the `docs/_build/html` directory.
