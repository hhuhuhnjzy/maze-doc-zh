# Configuration file for the Sphinx documentation builder.
# This is the Chinese conf.py

# -- Project information -----------------------------------------------------
project = 'Maze'
copyright = '2025, HUST'
author = 'HUST'
release = '0.1'
version = '0.1.0'

# ✅ 关键：设置语言为中文
language = 'zh_CN'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
    'sphinxcontrib.httpdomain',
    'sphinx_copybutton',
]

# Intersphinx mapping
intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}
intersphinx_disabled_domains = ['std']

templates_path = ['_templates']

# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinx_rtd_theme'

html_theme_options = {
    'collapse_navigation': False,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False,
}

# -- Options for EPUB output -------------------------------------------------
epub_show_urls = 'footnote'

# -- Additional settings -----------------------------------------------------
highlight_language = 'python'
suppress_warnings = ['ref.citation']