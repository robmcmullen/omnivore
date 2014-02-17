# Makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = sphinx-build
PAPER         = letter
BUILDDIR      = _build

# Internal variables.
PAPEROPT_a4     = -D latex_paper_size=a4
PAPEROPT_letter = -D latex_paper_size=letter
ALLSPHINXOPTS   = -d _build/doctrees $(PAPEROPT_$(PAPER)) $(SPHINXOPTS) .

.PHONY: help clean html htmlhelp latex pdf

all: html htmlhelp pdf

clean:
	-rm -rf $(BUILDDIR)/*

html:
	mkdir -p $(BUILDDIR)/html $(BUILDDIR)/doctrees
	$(SPHINXBUILD) -b html $(ALLSPHINXOPTS) $(BUILDDIR)/html

htmlhelp:
	mkdir -p $(BUILDDIR)/htmlhelp $(BUILDDIR)/doctrees
	$(SPHINXBUILD) -b htmlhelp $(ALLSPHINXOPTS) $(BUILDDIR)/htmlhelp
	#sphinx-wxoptimize -o ../peppy2/help $(BUILDDIR)/htmlhelp

latex:
	mkdir -p $(BUILDDIR)/latex $(BUILDDIR)/doctrees
	$(SPHINXBUILD) -b latex $(ALLSPHINXOPTS) $(BUILDDIR)/latex

pdf: latex
	-(cd $(BUILDDIR)/latex; make)
