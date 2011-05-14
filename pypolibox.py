#!/usr/bin/env python
# -*- coding: utf-8 -*-

# TODO: remove empty frozensets from message generation!

import sys
from time import time
import locale

from database import Query, Results, Book, Books
from facts import Facts, AllFacts
from propositions import Propositions, AllPropositions
from textplan import DocPlan, DocumentPlans, Message, Messages, AllMessages, ConstituentSet, Rule, Rules, generate_textplan
import debug

language, encoding = locale.getlocale()
DEFAULT_ENCODING = encoding # sqlite stores strings as unicode, but the user input is likely something else
  



if __name__ == "__main__":
    q = Query(sys.argv[1:])
    results = Results(q)
    print results
