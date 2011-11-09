#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Arne Neumann <arne-neumann@web.de>

"""
The pypolibox module is the 'main' module of the pypolibox package. It's the 
module you'd usually call from the command line or load into your Python 
interpreter. It just imports all the important modules and runs some demo 
code in case it is run from the command line without any arguments.
"""

import sys

from database import Query, Results, Book, Books
from facts import Facts, AllFacts
from propositions import Propositions, AllPropositions
from textplan import TextPlan, TextPlans, generate_textplan
from messages import Message, Messages, AllMessages
from rules import ConstituentSet, Rule, Rules
import debug


if __name__ == "__main__":
    query = Query(sys.argv[1:])
    books = Books(Results(query))
    print books
    print TextPlans(AllMessages(AllPropositions(AllFacts(books))))
