#p -*- coding: utf-8 -*-
#
# omnivore documentation build configuration file, created by
# sphinx-quickstart on Thu May  8 15:35:23 2008.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# All configuration values have a default value; values that are commented out
# serve to show the default value.

import sys, os

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
sys.path.append(os.path.abspath('..'))

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
#extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General substitutions.
project = 'Omnivore'
copyright = '2008-2014, Rob McMullen'

import omnivore
# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
version = omnivore.__version__
# The full version, including alpha/beta/rc tags.
release = omnivore.__version__

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%d %B %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directories, that shouldn't be searched
# for source files.
#exclude_dirs = []

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'


# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
html_style = 'default.css'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = "%s %s User Manual" % (project, version)

# The name of an image file (within the static path) to place at the top of
# the sidebar.
#html_logo = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
html_last_updated_fmt = '%d %b %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
html_use_modindex = False

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'omnivoredoc'


# Options for LaTeX output
# ------------------------

latex_elements = {
    'fncychap': '\\usepackage[Bjarne]{fncychap}',
    'fontpkg': '\\usepackage{times}',
    'papersize': 'letter',
    'pointsize': '10pt',
    'preamble': '',
    'maketitle': r"""\begin{titlepage}
 
\newcommand{\HRule}{\rule{\linewidth}{0.5mm}}
%% Title
\HRule \\[0.5cm]

\begin{minipage}{0.25\textwidth}
\begin{flushleft}
\includegraphics[width=1.0\textwidth]{../../_static/omnivore256.png}\\[1cm]
\end{flushleft}
\end{minipage}
\begin{minipage}{0.75\textwidth}
\begin{flushright}

{ \Huge \CTV Omnivore User Manual}\\[0.4cm]

\CTV{\Large Version %s}\\[0.5cm]
\end{flushright}
\end{minipage}

\vfill

\begin{flushright}
\CTV

\Large
Rob McMullen \\
\large
feedback@playermissile.com

\vfill

\end{flushright}

\begin{center}
\CTV
%% Bottom of the page
\vspace{1.0cm}
{\large \today}
 
\end{center}
\end{titlepage}
""" % version
    }

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual],
# toctree_only).
latex_documents = [
  ('index', 'UserManual.tex', 'Omnivore User Manual', 'Rob McMullen', 'manual', True),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
latex_use_modindex = True
