#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
pypolibox is part of a database-to-text generation (NLG) software and uses 
Python 2.7 and these modules (not included in the standard library):

    nltk, argparse
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
