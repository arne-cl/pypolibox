pypolibox
=========

*pypolibox* is a database-to-text generation (NLG) software built
on Python 2.7, *NLTK* and Nicholas FitzGerald's *pydocplanner*.

Using a database of technical books and some user input, pypolibox
generates sentences descriptions. These descriptions are then used by
the *OpenCCG* surface realiser to generate written sentences in German.


Installation
------------

Install from PyPI
~~~~~~~~~~~~~~~~~

::

    pip install pypolibox # prepend 'sudo' if needed


Install from source
~~~~~~~~~~~~~~~~~~~

::

    git clone https://github.com/arne-cl/pypolibox.git
    cd pypolibox
    python setup.py install # prepend 'sudo' if needed


In order to generate sentences (instead of abstract sentence
descriptions), you will need to install `OpenCCG`_ (tested with version
0.9.5). Make sure that at least ``tccg`` is in your ``$PATH``.
Under Linux, you'd have to add something like this to your ``.bashrc``:

::

    export PATH=/home/username/bin/openccg/bin:$PATH

    export OPENCCG_HOME=/home/username/bin/openccg
    export JAVA_HOME=/usr/lib/jvm/java-1.7.0-openjdk-amd64


.. _`OpenCCG`: http://openccg.sourceforge.net/


Usage
-----

``pypolibox`` can be used from the command line or from within a Python
interpreter. To see all the available options, enter::

    pypolibox -h

To find books that are written in German and use the
programming language Prolog, type::

    pypolibox --language German --proglang Prolog

or, if you prefer short but cryptic commands::

    pypolibox -l German -p Prolog

You can choose between several output formats using the ``-o`` or
``--output-format`` argument. The default option is ``openccg``, which
will generate sentences using OpenCCG. ``textplan`` will generate an XML
representation of the textplans and ``hlds`` will generate HLDS XML
representations of all the sentences.

    pypolibox --language German --proglang Prolog --output-format hlds

Further usage examples can be found in the ``pypolibox.database.Query``
class documentation. If you'd like to access ``pypolibox`` from
within a Python interpreter, you can simply use the same arguments.
Instead of a string like *-l German -p Prolog*, you will have to
provide your arguments as a list of strings::

    Query(["-l", "German", "-p", "Prolog"])

This query would be equivalent to the command line queries above.
``pypolibox`` is built as a pipeline, where each important step is
represented by a class. Each of these classes function as the input
of the next class in the pipeline, e.g.::

    query = Query(["-l", "German", "-p", "Prolog"])
    Results(query)
    Books(Results(query))
    ...
    TextPlans(AllMessages(AllPropositions(AllFacts(Books(Results(query))))))

If you instanciate a Query with your query arguments, you can use
this ``Query`` instance as the input of a ``Results`` instance
(which contains the data that the database provided for your query),
which in turn can be used as the input of a ``Books`` instance etc.

Of course, you wouldn't want to chain all those classes just to retrieve
textplans. To do so, simply use one of the functions provided in the
``debug`` module, either by running the ``debug.py`` file in
the interpreter or by importing it::

    import debug
    debug.gen_textplans(["-l", "German", "-p", "Prolog"])

This function call would return the same results as the aforementioned
command line calls. For further testing, try
``debug.testqueries`` and ``debug.error_testqueries``, which
basically are lists of predefined valid and invalid query arguments and which
can be used to query the database (and see how errors are handled).


Documentation
-------------

The documentation is available `online <http://pypolibox.readthedocs.org>`_,
but you can always get an up-to-date local copy using `Sphinx`_.

You can generate an HTML or PDF version by running these commands in
pypolibox's ``docs`` directory::

    make latexpdf

to produce a PDF (``docs/_build/latex/pypolibox.pdf``) and ::

    make html

to produce a set of HTML files (``docs/_build/html/index.html``).

.. _`Sphinx`: http://sphinx-doc.org/


Package Overview
----------------

The pypolibox package contains the following modules:

- The ``pypolibox`` module is the main module, which is invoked from the
  command line.
- The ``database`` module handles the user input, queries the database and
  returns the results.
- ``facts`` converts those results into attribute value matrices.
- The ``propositions`` module evaluates those facts (positive, negative,
  neutral).
- The ``textplan`` module takes those propositions and turns them into
  messages. In contrast to propositions, messages do not contain duplicates
  and add comparative information. Rules will be used to combine those
  message into constituent sets and ultimately into one text plan. The
  ``textplan`` module also allows exporting those text plans in XML format.
- The ``rules`` module contains the rules used by be the ``textplan`` module
  to combine messages into constituent sets and textplans, respectively.
- The ``messages`` module generates messages from propositions, which will
  be used by the ``textplan`` module.


- The ``lexicalize_messageblocks`` is the "main" module of the
  lexicalization. For each message block in a textplan, it generates one or
  more possible lexicalizations which are then realized by the
  ``realization`` module.
- The ``lexicalization`` module generates lexicalizations (in HLDS-XML
  format) for each message, which are used by the
  ``lexicalize_messageblocks`` module to form lexicalizations of complete
  message blocks.
- **A note on terminology**: A message block in ``pypolibox`` is basically an
  instance of the ``Message`` class, e.g an "id" message block. This
  "id" message block in turn consists of several messages, e.g. an
  "authors" message and a "title" message.
- The ``realization`` module takes a lexicalized phrase or sentence (in
  HLDS-XML format) and converts it into a surface realization (with the
  help of OpenCCGs ``tccg`` executable).
- The ``hlds`` module allows to convert textplans from a
  ``nltk.featstruct``-based format to HLDS-XML and vice versa. In addition, the
  module can produce attribute-value matrices of these textplans as
  LaTeX/PDF files.


Licence
-------

The code is licensed under GPL Version 3. The grammar fragment is licensed
under `Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License <http://creativecommons.org/licenses/by-nc-sa/4.0/>`_.

Author
------

Arne Neumann


Acknowledgements
----------------

This software reimplements parts of the Java-based *JPolibox*
text-generation software written by Alexandra Strelakova, Felix Dombek,
Mathias Langer and Till Kolter. pypolibox also includes a heavily
modified version of Nicholas FitzGerald's *pydocplanner*, which he
released under a Creative Commons license (not specified further).
The German OpenCCG grammar fragment that comes with pypolibox was written by
Martin Oltmann.
