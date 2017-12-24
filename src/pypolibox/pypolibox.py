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
from textplan import (TextPlan, TextPlans, generate_textplan,
                      linearize_textplan, textplans2xml)
from hlds import etreeprint
from messages import Message, Messages, AllMessages
from rules import ConstituentSet, Rule, Rules


def test():
    """test and realize all text plans for all test queries"""
    import cPickle
    atp = cPickle.load(open("data/alltextplans.pickle", "r"))
    for textplans in atp:
        for textplan in textplans.document_plans:
            check_and_realize_textplan(textplan)


def generate_textplans(query):
    """generates all text plans for a database query"""
    books = Books(Results(query))
    return TextPlans(AllMessages(AllPropositions(AllFacts(books))))


def initialize_openccg():
    """
    starts OpenCCG's tccg realizer as a server in the background (ca. 20s).
    """
    from realization import OpenCCG
    return OpenCCG()


def check_and_realize_textplan(openccg, textplan, lexicalize_messagle_block, phrase2sentence):
    """
    realizes a text plan and warns about message blocks that cannot be
    realized due to current restrictions in the OpenCC grammar.

    Parameters
    ----------
    openccg : OpenCCG
        a running OpenCCG instance
    textplan : TextPlan
        text plan to be realized
    """
    msg_blocks = linearize_textplan(textplan)
    for msg_block in msg_blocks:
        try:
            lexicalized_msg_block = lexicalize_message_block(msg_block)
            print "The {0} message block can be realized " \
                  "as follows:\n".format(msg_block[Feature("msgType")])
            for lexicalized_phrase in lexicalized_msg_block:
                lexicalized_sentence = phrase2sentence(lexicalized_phrase)
                for realized_sent in openccg.realize(lexicalized_sentence):
                    print realized_sent

        except NotImplementedError, err:
            print err
            print "The message block contains these messages:\n", msg_block, \
                  "\n\n**********\n\n"
        print

def main():
    """
    This is the pypolibox commandline interface. It allows you to query
    the database and generate book recommendatins, which will either be
    handed to OpenCCG for generating sentences or printed to stdout in
    an XML format representing the text plans.
    """
    query = Query(sys.argv[1:])

    output_format = query.query_args.output_format
    valid_output_formats = ['openccg', 'hlds', 'textplan-xml', 'textplan-featstruct']
    if output_format not in valid_output_formats:
        sys.stderr.write("Output format must be one of: {}\n".format(valid_output_formats))
        sys.exit(1)

    try:
        lexicalize_messageblocks =
          __import__("lexicalize_messageblocks_%s" % query.args.output_language, globals(), locals(), [], -1))
    except ImportError:
        raise

    try:
        lexicalization =
          __import__("lexicalization_%s" % query.args.output_language, globals(), locals(), [], -1))
    except ImportError:
        raise

    lexicalize_message_block = lexicalize_messageblocks.lexicalize_message_block
    phrase2sentence = lexicalization.phrase2sentence


    textplans = generate_textplans(query)

    if output_format == 'openccg':
        openccg = initialize_openccg(lang=query.args.output_language)
        print "{} text plans will be generated.".format(len(textplans.document_plans))
        for i, textplan in enumerate(textplans.document_plans):
            print "Generating text plan #%i:\n" % i
            check_and_realize_textplan(openccg, textplan, lexicalize_message_block, phrase2sentence)
    elif output_format == 'hlds':
        from copy import deepcopy
        from hlds import (Diamond, Sentence, diamond2sentence,
            add_nom_prefixes, create_hlds_file)

        for i, textplan in enumerate(textplans.document_plans):
            print "Text plan #%i:\n" % i

            # TODO: refactor to avoid code duplication w/
            # check_and_realize_textplan()
            msg_blocks = linearize_textplan(textplan)
            for msg_block in msg_blocks:
                try:
                    lexicalized_msg_block = lexicalize_message_block(msg_block)
                    print "The {0} message block can be realized " \
                          "as follows:\n".format(msg_block[Feature("msgType")])
                    for lexicalized_phrase in lexicalized_msg_block:
                        lexicalized_sentence = phrase2sentence(lexicalized_phrase)

                        # TODO: refactor to avoid duplication w/ OpenCCG.realize
                        temp_sentence = deepcopy(lexicalized_sentence)

                        if isinstance(lexicalized_sentence, Diamond):
                            temp_sentence = diamond2sentence(temp_sentence)

                        add_nom_prefixes(temp_sentence)
                        print create_hlds_file(temp_sentence,
                            mode="realize", output="xml")

                except NotImplementedError, err:
                    print err
                    print "The message block contains these messages:\n", msg_block, \
                          "\n\n**********\n\n"

    elif output_format == 'textplan-featstruct':
        for i, textplan in enumerate(textplans.document_plans):
            print "Text plan #%i:\n" % i
            print textplan, "\n\n"

    else: # output_format == 'textplan-xml'
        etreeprint(textplans2xml(textplans))


if __name__ == "__main__":
    main()
