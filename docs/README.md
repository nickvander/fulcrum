# About This Documentation

This directory contains the source files and configuration for the Fulcrum
project's official technical documentation.

The content of the documentation can be found in the `docs/source/` directory.

## Contributing to the Documentation

We welcome contributions to improve the documentation. This section explains the
technical setup for building the documentation locally.

### Tech Stack

The documentation is built using [Sphinx](https://www.sphinx-doc.org/), a
powerful documentation generator, and written in Markdown using the
[MyST parser](https://myst-parser.readthedocs.io/).

### Local Development & Preview

To work on the documentation, you can run a live-reloading web server that will
automatically rebuild the site whenever you save a file.

1.  **Set up your local environment:** Follow the
    **[Backend Setup Guide](./source/backend-setup.md)** to install `uv` and
    create a virtual environment.
2.  **Run the server:** From the project root, run the `docs:serve` command:

    ```bash
    npm run docs:serve
    ```

This command will install the necessary documentation dependencies and start the
server. It should automatically open the documentation site in your default web
browser.
