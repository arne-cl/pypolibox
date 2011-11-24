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
from nltk.featstruct import Feature

from database import Query, Results, Book, Books
from facts import Facts, AllFacts
from propositions import Propositions, AllPropositions
from textplan import TextPlan, TextPlans, generate_textplan, linearize_textplan
from messages import Message, Messages, AllMessages
from rules import ConstituentSet, Rule, Rules
from lexicalization import phrase2sentence
from lexicalize_messageblocks import lexicalize_message_block
from realization import OpenCCG
from util import load_settings
    
SETTINGS = load_settings()
openccg = OpenCCG(SETTINGS)

if __name__ == "__main__":
    query = Query(sys.argv[1:])
    books = Books(Results(query))
    textplans = TextPlans(AllMessages(AllPropositions(AllFacts(books))))
    
    for textplan in textplans.document_plans:
        msg_blocks = linearize_textplan(textplan)
        for msg_block in msg_blocks:
            try:
                lexicalized_msg_block = lexicalize_message_block(msg_block)            
            except:
                print "this message block can't be realized, but contains " \
                      "these basic facts ... \n\n"
                continue

            print "The {0} message block can be realized " \
                  "as follows:\n".format(msg_block[Feature("msgType")])
            for lexicalized_phrase in lexicalized_msg_block:
                lexicalized_sentence = phrase2sentence(lexicalized_phrase)
                for realized_sent in openccg.realize(lexicalized_sentence):
                    print realized_sent

            print "\n"

# TODO: add textplanner XML output format
# TODO: add max_textplans paramter --> generate only the X highest ranking books
# TODO: add .info() method to TextPlan, which should describe verbally if a TP
#       describing one book or comparing two books

"""
lexicalization.py doctest starts automatically, now.
removed lexicalize_lastbook_nomatch() (can't be realized)
added realization to pypolibox.py
"""
