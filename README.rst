pypolibox
=========

*pypolibox* is a database-to-text generation (NLG) software built
on Python 2.6, *NLTK* and Nicholas FitzGerald's *pydocplanner*.

Using a database of technical books and some user input, pypolibox
generates sentences descriptions. These descriptions are then used by
the *OpenCCG* surface realiser to generate written sentences in German.


Installation
------------

Please install Python 2.6 (or 2.7), python-nltk and python-argparse
before running pypolibox.

In order to generate sentences (instead of abstract sentence
descriptions), you will need to install `OpenCCG`_ (tested with version
0.9.5). You will also need a copy of the correspoding German OpenCCG
grammar fragment (written by Martin Oltmann, not released yet).

.. _`OpenCCG`: http://openccg.sourceforge.net/

Usage
-----

Please see `__init__.py` (and/or generate the complete documentation
with epydoc).


Licence
-------

GPL Version 3.

Author
------

Arne Neumann


Acknowledgements
----------------

This software reimplements parts of the Java-based _JPolibox_
text-generation software written by Alexandra Strelakova, Felix Dombek,
Mathias Langer and Till Kolter. pypolibox also includes a heavily
modified version of Nicholas FitzGerald's *pydocplanner*, which he
released under a CreativeCommons license (not specified further).
