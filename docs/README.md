# Fulcrum Documentation

This directory contains the source files for the Fulcrum project's official
documentation.

## Tech Stack

The documentation is built using [Sphinx](https://www.sphinx-doc.org/), a
powerful documentation generator, and written in Markdown using the
[MyST parser](https://myst-parser.readthedocs.io/). This allows us to write
easy-to-read documentation in a familiar syntax while leveraging the power and
extensibility of Sphinx.

The site is automatically built and deployed to GitHub Pages whenever a change
is merged into the `main` branch.

## Local Development

To work on the documentation locally, you can run a live-reloading web server.
This allows you to see your changes in real-time as you edit the files.

### Prerequisites

-   Python 3
-   Node.js and npm

### Running the Server

1.  **Navigate to the project root.**
2.  **Run the `docs:serve` command:**

    ```bash
    npm run docs:serve
    ```

This command will first install all the necessary Python dependencies and then
start the server. It should automatically open the documentation site in your
default web browser.

## Directory Structure

-   `docs/source/`: This directory contains all the raw documentation content,
    written as Markdown (`.md`) files. The main entrypoint and navigation tree
    is defined in `docs/source/index.rst`.
-   `docs/conf.py`: The main Sphinx configuration file.
-   `docs/requirements.txt`: Contains the Python dependencies required to build
    the documentation.
-   `docs/_build/`: This directory is created when you build the documentation
    and contains the final HTML output. It is ignored by Git.
