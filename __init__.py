# pypolibox
# Author: Arne Neumann <arne-neumann@web.de>

"""
Welcome to the I{pypolibox} documentation!

There's a plain text version of this document (I{README} or I{__init__.py} in
pypolibox's main directory), but you could also read the PDF
(I{doc/latex/api.pdf}) or HTML version (I{doc/html/index.html}) instead.

I{pypolibox} is part of a database-to-text generation (NLG) software built on
Python 2.6, the Natural Language Toolkit I{NLTK} and Nicholas Fitzgerald's
I{pydocplanner}. pypolibox is a reimplementation of I{JPolibox} (not Polibox)
and therefore shares some of its oddities.

Installation
============

Please install Python 2.6, python-nltk and python-argparse before running
I{pypolibox}.

Usage
=====

I{pypolibox} can be used from the command line or from within a Python
interpreter. To see all the available options, enter::

    python pypolibox.py -h

To find books that are written in German and use the
programming language Prolog, type::

    python pypolibox.py --language German --proglang Prolog

or, if you prefer short but cryptic commands::

    python pypolibox.py -l German -p Prolog

If you're just interested in text plans (as opposed to generated sentences),
add the -x or --xml command line option::

    python pypolibox.py --language German --proglang Prolog --xml

Further usage examples can be found in the L{Query<pypolibox.database.Query>}
class documentation. If you'd like to access I{pypolibox} from within a Python
interpreter, you can simply use the same arguments. Instead of a string like
I{-l German -p Prolog}, you will have to provide your arguments as a list of
strings::

    Query(["-l, "German", "-p", "Prolog"])

This query would be equivalent to the command line queries above.
I{pypolibox} is built as a pipeline, where each important step is represented
by a class. Each of these classes function as the input of the next class in
the pipeline, e.g.::

    query = Query(["-l, "German", "-p", "Prolog"])
    Results(Query(query))
    Books(Results(Query(query)))
    ...
    TextPlans(AllMessages(AllPropositions(AllFacts(Books(Results(Query(query)))))))

If you instanciate a Query with your query arguments, you can use this
C{Query} instance as the input of a C{Results} instance (which contains the
data that the database provided for your query), which in turn can be used as
the input of a C{Books} instance etc.

Of course, you wouldn't want to chain all those classes just to retrieve
textplans. To do so, simply use one of the functions provided in the
L{debug<pypolibox.debug>} module, either by running the I{debug.py} file in
the interpreter or by importing it::

    import debug
    debug.gentextplans(["-l, "German", "-p", "Prolog"])

This function call would return the same results as the aforementioned
command line calls. For further testing, try
L{debug.testqueries<pypolibox.debug.testqueries>} and
L{debug.error_testqueries<pypolibox.debug.error_testqueries>}, which
basically are lists of predefined valid and invalid query arguments and which
can be used to query the database (and see how errors are handled).


Updating the documentation
==========================

This documentation was created by using I{epydoc}, a program that converts
docstring comments (added manually to Python functions, methods and classes)
into a human-friendly format (PDF, HTML). If you add to or change those
docstrings, please don't forget to update the epydoc documentation for fellow
humanoids. This can be done by running these commands in pypolibox's main
directory::

    epydoc --pdf --name pypolibox --output doc/latex .

to produce a PDF version and ::

    epydoc --html --name pypolibox --graph all --output doc/html .

to produce an HTML version.


Package Overview
================

G{packagetree}

The pypolibox package contains the following modules:

    - The I{pypolibox} module is the main module, which is invoked from the
      command line.
    - The I{database} module handles the user input, queries the database and
      returns the results.
    - I{facts} converts those results into attribute value matrices.
    - The I{propositions} module evaluates those facts (positive, negative,
      neutral).
    - The I{textplan} module takes those propositions and turns them into
      messages. In contrast to propositions, messages do not contain duplicates
      and add comparative information. Rules will be used to combine those
      message into constituent sets and ultimately into one text plan. The
      I{textplan} module also allows exporting those text plans in XML format.
    - The I{rules} module contains the rules used by be the I{textplan} module
      to combine messages into constituent sets and textplans, respectively.
    - The I{messages} module generates messages from propositions, which will
      be used by the I{textplan} module.


    - The I{lexicalize_messageblocks} is the "main" module of the
      lexicalization. For each message block in a textplan, it generates one or
      more possible lexicalizations which are then realized by the
      I{realization} module.
    - The I{lexicalization} module generates lexicalizations (in HLDS-XML
      format) for each message, which are used by the
      I{lexicalize_messageblocks} module to form lexicalizations of complete
      message blocks.
      TERMINOLOGY NOTE: A message block in I{pypolibox} is basically an
      instance of the C{Message} class, e.g an "id" message block. This
      "id" message block in turn consists of several messages, e.g. an
      "authors" message and a "title" message.
    - The I{realization} module takes a lexicalized phrase or sentence (in
      HLDS-XML format) and converts it into a surface realization (with the
      help of I{OpenCCG}s tccg executable).
    - The I{hlds} module allows to convert textplans from a
      nltk.featstruct-based format to HLDS-XML and vice versa. In addition, the
      module can produce attribute-value matrices of these textplans as
      LaTeX/PDF files.


to-do list
==========

    - THEORY/STRUCTURE: Rewrite rules for the textplanner. RST relations should
      combine messages, not message blocks. (A message should be something that
      can be expressed in a single sentence.)
    - COVERAGE: Update the lexicalization module once Martin's grammar is
      "completed".
    - CONSISTENCY: Make keys unique. Instead of three different "recency" keys,
      there should be a regular one, an "extra_recency" key ('This book is
      particularly recent/old') and a "relative_recency" key ('This book is 20
      years older than the other one').
    - CONSISTENCY: In "extra recency" messages, "values" are called
      "descriptions".
    - CLUTTER: Get rid of ratings whenever possible. At least remove all
      "neutral" ratings.
    - STRUCTURE: Do we really need both facts and propositions?
    - UNICODE: If NLTK becomes available for Python 3, switch to that branch.
      Otherwise, evaluate if porting nltk.featstruct to Python 3 is feasible
      (e.g. with the help of python2to3).
    - DOCUMENTATION: epydoc is dead. switch to sphinx with autodoc.

"""
