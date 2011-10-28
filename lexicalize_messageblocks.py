#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Arne Neumann <arne-neumann@web.de>

import cPickle as pickle # TODO: dbg, rm
from nltk.featstruct import Feature, FeatDict

from hlds import Diamond, create_diamond, add_mode_suffix
from lexicalization import *
from realization import realize as realizer #TODO: dbg, mv to main


def load_all_textplans():
    f = open("data/alltextplans-20111028.pickle","r")
    return pickle.load(f)


def lexicalize_message_block(messageblock):
    msg_type = messageblock[Feature("msgType")]
    lexicalize_function_name = "lexicalize_" + msg_type
    return eval(lexicalize_function_name)(messageblock)



def lexicalize_id(id_message_block):
    r"""
    pass all the messages directly to their respective lexicalization
    functions.
    """
    lexicalized_messages = []
    for msg_name, msg_val in id_message_block.items():
        if isinstance(msg_name, str): # don't process C{Feature}s
            lexicalize_function_name = "lexicalize_" + msg_name
            lexicalized_messages += eval(lexicalize_function_name)(msg_val)
    return lexicalized_messages

def lexicalize_extra(extra_message_block):
    r"""
    außerdem / zusätzlich / hinzu kommt
    """
    pass

def lexicalize_lastbook_match(lastbook_match_message_block):
    r"""sowohl als auch / beide Bücher / gemeinsam ist beiden Büchern"""
    pass

def lexicalize_lastbook_nomatch(lastbook_nomatch_message_block):
    r"""im Gegensatz zu / wohingegen"""
    pass

def fake_lastbook_nomatch(lexicalized_lastbook_message, lexicalized_message):
    r"""
    dieses Buch _____, wohingegen das erste Buch ____

    >>> title = lexicalize_titles(["foo"], realize="pronoun")
    >>> lasttitle = lexicalize_titles(["Angewandte Computerlinguistik"], realize="complete")
    >>> lang = lexicalize_language("German", title, realize="noun")
    >>> lastlang = lexicalize_language("English", lasttitle, realize="adjective")
    >>> realizer(fake_lastbook_nomatch(lastlang, lang))
    ['es ist auf Deutsch , wohingegen \xe2\x80\x9e Angewandte_Computerlinguistik \xe2\x80\x9c in englischer Sprache ist']
    """
    hs = lexicalized_message
    hs.change_mode("HS")

    vl = lexicalized_lastbook_message
    vl.change_mode("VL")

    ns = create_diamond("NS", "adversativ", "wohingegen", [vl])

    return create_diamond("", "subjunktion", "komma", [hs, ns])



def lexicalize_usermodel_match(usermodel_match_message_block):
    r"""erfüllt Anforderungen / entspricht ihren Wünschen"""
    pass

def lexicalize_usermodel_nomatch(usermodel_nomatch_message_block):
    r"""erfüllt (leider) Anforderungen nicht / entspricht nicht ihren
    Wünschen"""
    pass
