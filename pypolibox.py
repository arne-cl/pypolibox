#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
I{pypolibox} is part of a database-to-text generation (NLG) software built on 
Python 2.6, the Natural Language Toolkit I{NLTK} and Nicholas Fitzgerald's 
I{pydocplanner}. pypolibox is a reimplementation of I{JPolibox} and therefore 
shares some of its oddities. 

External dependencies: python2.6, python-nltk, python-argparse
"""

import sys

from database import Query, Results, Book, Books
from facts import Facts, AllFacts
from propositions import Propositions, AllPropositions
from textplan import (TextPlan, TextPlans, Message, Messages, AllMessages, 
                      ConstituentSet, Rule, Rules, generate_textplan)
import debug


if __name__ == "__main__":
    query = Query(sys.argv[1:])
    books = Books(Results(query))
    print books
    print TextPlans(AllMessages(AllPropositions(AllFacts(books))))
