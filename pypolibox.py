#!/usr/bin/env python
# -*- coding: utf-8 -*-

# TODO: remove empty frozensets from message generation!

import sys

from database import Query, Results, Book, Books
from facts import Facts, AllFacts
from propositions import Propositions, AllPropositions
from textplan import TextPlan, TextPlans, Message, Messages, AllMessages, ConstituentSet, Rule, Rules, generate_textplan
import debug




if __name__ == "__main__":
    query = Query(sys.argv[1:])
    books = Books(Results(query))
    print books
    print TextPlans(AllMessages(AllPropositions(AllFacts(books))))
