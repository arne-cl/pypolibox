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
from textplan import TextPlan, TextPlans, generate_textplan, linearize_textplan
from messages import Message, Messages, AllMessages
from rules import ConstituentSet, Rule, Rules
from lexicalize_messageblocks import lexicalize_message_block
import debug


if __name__ == "__main__":
    query = Query(sys.argv[1:])
    books = Books(Results(query))
    textplans = TextPlans(AllMessages(AllPropositions(AllFacts(books))))
    for textplan in textplans.document_plans[-3:]:
    # realize only the three highest ranking books
        msg_blocks = linearize_textplan(textplan)
        for msg_block in msg_blocks:
            lexicalized = lexicalize_message_block(msg_block)
            print lexicalized
