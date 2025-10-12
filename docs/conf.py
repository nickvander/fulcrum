# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Fulcrum'
copyright = '2025, Nick Van der Auwermeulen'
author = 'Nick Van der Auwermeulen'
release = ''

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'myst_parser',
    'sphinx_copybutton',
    'sphinxcontrib.mermaid',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

source_suffix = {
    '.rst': 'restructuredtext',
    '.txt': 'markdown',
    '.md': 'markdown',
}


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'furo'
html_static_path = ['_static']

html_theme_options = {
    "light_css_variables": {
        "color-background-primary": "#f5f5f5",
        "color-background-secondary": "#ffffff",
        "color-content-foreground": "#2d2d2d",
        "color-content-secondary": "#5f5f5f",
        "color-brand-primary": "#2962ff",
        "color-brand-content": "#2962ff",
        "color-sidebar-background": "#e8e8e8",
        "color-sidebar-link-text": "#2d2d2d",
        "color-sidebar-link-text--top-level": "#2d2d2d",
        "color-admonition-background": "#e8e8e8",
    },
    "dark_css_variables": {
        "color-background-primary": "#1e1e1e",
        "color-background-secondary": "#2c2c2c",
        "color-content-foreground": "#d4d4d4",
        "color-content-secondary": "#a0a0a0",
        "color-brand-primary": "#56b6c2",
        "color-brand-content": "#56b6c2",
        "color-sidebar-background": "#252526",
        "color-sidebar-link-text": "#d4d4d4",
        "color-sidebar-link-text--top-level": "#d4d4d4",
        "color-admonition-background": "#2c2c2c",
    },
}

# -- Options for syntax highlighting ---------------------------------------
pygments_style = "tango"  # Style for light mode
pygments_dark_style = "material"  # Style for dark mode

