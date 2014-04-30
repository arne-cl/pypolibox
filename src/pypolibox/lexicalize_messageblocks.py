#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Arne Neumann <arne-neumann@web.de>

"""
The C{lexicalize_messageblocks} module realizes message blocks which
consist of one or more messages.
"""

import random
from copy import deepcopy
from nltk.featstruct import Feature

from hlds import Diamond, create_diamond
from lexicalization import (gen_art, gen_num,
    lexicalize_authors, lexicalize_codeexamples, lexicalize_exercises,
    lexicalize_keywords, lexicalize_language, lexicalize_length,
    lexicalize_pages, lexicalize_proglang, lexicalize_recency,
    lexicalize_target, lexicalize_title, lexicalize_title_description,
    lexicalize_year)

#from debug import gen_all_messages_of_type, printeach #TODO: dbg, rm

#~ def enumrealize(diamond_list):
    #~ """debugging function that realizes a list of diamonds, one at a time"""
    #~ for diamond in diamond_list:
        #~ printeach(openccg.realize(diamond))

#~ def test(msg_type="id", block_number=0):
    #~ msg_blocks = gen_all_messages_of_type(msg_type)
    #~ lexicalized_msgs = lexicalize_message_block(msg_blocks[block_number])
    #~ return [phrase2sentence(msg) for msg in lexicalized_msgs]

def lexicalize_message_block(messageblock):
    msg_type = messageblock[Feature("msgType")]
    lexicalize_function_name = "lexicalize_" + msg_type
    return eval(lexicalize_function_name)(messageblock)


def lexicalize_authors_variations(authors):
    r"""
    lexicalize all the possible variations of author descriptions and put
    them in a dictionary, so other functions can easily choose one of them.

    @type authors_tuple: C{tuple} of (C{frozenset} of C{str}, C{str})
    @param author_tuple: tuple containing a set of names, e.g. (["Ronald
    Hausser", "Christopher D. Manning"]) and a rating, i.e. "neutral"

    @rtype: C{dict} of C{str}, C{Diamond} key-value pairs
    @return: "abstract" lexicalizes "der Autor" or "die Autoren", "complete"
    realizes a list of author names (incl. surname), and "lastnames" realizes
    a list of author last names.

    >>> authors_variations = lexicalize_authors_variations((frozenset(["Christopher Manning", "Alan Kay"]),""))
    >>> openccg.realize(authors_variations["complete"])
    ['Christopher Manning und Alan Kay', 'Christopher Mannings und Alan Kays']

    >>> openccg.realize(authors_variations["lastnames"])
    ['Manning und Kay', 'Mannings und Kays']

    >>> openccg.realize(authors_variations["abstract"])
    ['den Autoren', 'der Autoren', 'die Autoren']
    """
    authors_variations = {}
    for variation in ("abstract", "complete", "lastnames"):
        authors_variations[variation] = lexicalize_authors(authors,
                                                           realize=variation)
    return authors_variations

def lexicalize_title_variations(title, authors):
    r"""
    generates several book title lexicalizations and stores them in a C{dict}.
    
    @type title: C{tuple} of (C{str}, C{str})
    @param title: tuple containing a book title and a rating (neutral)
    @rtype: C{dict} of C{str}, C{Diamond} key-value pairs

    generate several different lexicalizations of book title / author
    combinations:
    >>> title_variations = lexicalize_title_variations(("Angewandte Computerlinguistik", ""), (set(["David Cole"]), ""))

    realize "das Buch":
    >>> openccg.realize(title_variations["abstract"])
    ['das Buch', 'dem Buch', 'des Buches']

    realize "es" (in the meaning of "it" / "the book"):
    >>> openccg.realize(title_variations["pronoun"])
    ['es', 'ihm', 'seiner']

    realize "$booktitle":
    >>> openccg.realize(title_variations["complete"])
    ['\xe2\x80\x9e Angewandte_Computerlinguistik \xe2\x80\x9c']

    realize "$fullname's $booktitle":
    >>> openccg.realize(title_variations["title+complete-names-possessive"])
    ['David Coles \xe2\x80\x9e Angewandte_Computerlinguistik \xe2\x80\x9c']

    realize "$lastname's $booktitle":
    >>> openccg.realize(title_variations["title+lastnames-possessive"])
    ['Coles \xe2\x80\x9e Angewandte_Computerlinguistik \xe2\x80\x9c']

    realize "$booktitle von $fullname":
    >>> openccg.realize(title_variations["title+complete-names-preposition"])
    ['\xe2\x80\x9e Angewandte_Computerlinguistik \xe2\x80\x9c von David Cole']

    realize "$booktitle von $lastname":
    >>> openccg.realize(title_variations["title+lastnames-preposition"])
    ['\xe2\x80\x9e Angewandte_Computerlinguistik \xe2\x80\x9c von Cole']

    realize "das Buch von $fullname":
    >>> openccg.realize(title_variations["abstract-title+complete-names-preposition"])
    ['das Buch von David Cole', 'dem Buch von David Cole', 'des Buches von David Cole']

    realize "das Buch von $lastname":
    >>> openccg.realize(title_variations["abstract-title+lastnames-preposition"])
    ['das Buch von Cole', 'dem Buch von Cole', 'des Buches von Cole']
    """
    title_variations = {} #"abstract", "complete", "pronoun" or "authors+title"
    for variation in ("abstract", "complete", "pronoun"):
        title_variations[variation] = lexicalize_title(title,
                                                       realize=variation)

    authors_variations = lexicalize_authors_variations(authors)

    # Noam Chomskys „On Syntax“
    title_variations["title+complete-names-possessive"] = \
        lexicalize_title(title, authors_variations["complete"],
                         realize="complete", authors_realize="possessive")
    # Chomskys „On Syntax“
    title_variations["title+lastnames-possessive"] = \
        lexicalize_title(title, authors_variations["lastnames"],
                         realize="complete", authors_realize="possessive")
    # „Buchtitel“ von Christopher Manning und Alan Kay
    title_variations["title+complete-names-preposition"] = \
        lexicalize_title(title, authors_variations["complete"],
                         realize="complete", authors_realize="preposition")
    # „Buchtitel“ von Manning und Kay
    title_variations["title+lastnames-preposition"] = \
        lexicalize_title(title, authors_variations["lastnames"],
                         realize="complete", authors_realize="preposition")
    # das Buch von Christopher Manning und Alan Kay
    title_variations["abstract-title+complete-names-preposition"] = \
        lexicalize_title(title, authors_variations["complete"],
                         realize="abstract", authors_realize="preposition")
    # das Buch von Manning und Kay
    title_variations["abstract-title+lastnames-preposition"] = \
        lexicalize_title(title, authors_variations["lastnames"],
                         realize="abstract", authors_realize="preposition")

    return title_variations


def lexicalize_id(id_message_block):
    r"""
    lexicalize all the messages contained in an id message block
    (aka C{Message})

    @type: C{Message}
    @param: a message (of type "id")
    
    @rtype: C{List} of C{Diamond}s
    @return: a list of lexicalized phrases, which can be realized with
    I{tccg} directly or turned into sentences beforehand with C{lexicalization.phrase2sentence} to remove ambiguity
    """
    assert id_message_block[Feature("msgType")] == "id"
    
    msg_block = deepcopy(id_message_block)
    authors = msg_block["authors"]
    title = msg_block["title"]
    #author_variations = lexicalize_authors_variations(authors)
    title_variations = lexicalize_title_variations(title, authors)

    lxed_phrses = []
    if "year" in msg_block:
        lxed_phrses.append(lexicalize_title_description(msg_block["title"],
                                                        msg_block["authors"],
                                                        msg_block["year"]))
    else:
        lxed_phrses.append(lexicalize_title_description(msg_block["title"],
                                                        msg_block["authors"]))

    identifiers = set(["title", "authors", "year"])
    for msg_name, msg in msg_block.items():
        if isinstance(msg_name, Feature) or msg_name in identifiers:
            msg_block.pop(msg_name)

    msg_names = msg_block.keys()

    if "codeexamples" in msg_names:
        if "proglang" in msg_names and msg_block["proglang"][0]:
            # proglang should not be realized if the book doesn't use one
            lexicalized_proglang = lexicalize_proglang(msg_block["proglang"],
                                                       realize="embedded")
            lxed_phrses.append(lexicalize_codeexamples(
                                    msg_block["codeexamples"],
                                    lexicalized_proglang,
                                    random_variation(title_variations),
                                    lexeme="random"))
            msg_block.pop("proglang")
        else:
            lxed_phrses.append(
                lexicalize_codeexamples(msg_block["codeexamples"],
                                        random_variation(title_variations),
                                        lexeme="random"))
        msg_block.pop("codeexamples")

    for msg_name, msg in msg_block.items():
        lexicalize_function_name = "lexicalize_" + msg_name
        lxed_phrses.append(
            eval(lexicalize_function_name)(msg,
                        lexicalized_title=random_variation(title_variations)))
    return lxed_phrses


def lexicalize_extra(extra_message_block):
    r"""
    lexicalize all the messages contained in an extra message block
    (aka C{Message})

    @type: C{Message}
    @param: a message (of type "extra")
    
    @rtype: C{List} of C{Diamond}s
    @return: a list of lexicalized phrases, which can be realized with
    I{tccg} directly or turned into sentences beforehand with C{lexicalization.phrase2sentence} to remove ambiguity
    
    NOTE: "außerdem" works only in a limited number of contexts, e.g. 'das
    Buch ist neu, außerdem ist es auf Deutsch' but not 'das Buch ist neu,
    außerdem ist das Buch auf Deutsch'. therefore, no connective is used here
    so far.
    """
    assert extra_message_block[Feature("msgType")] == "extra"
    
    msg_block = deepcopy(extra_message_block)
    authors = msg_block[Feature("reference_authors")]
    title = msg_block[Feature("reference_title")]
    #author_variations = lexicalize_authors_variations(authors)
    title_variations = lexicalize_title_variations(title, authors)

    lxed_phrses = []
    for msg_name, msg in msg_block.items():
        if isinstance(msg_name, str):
            lexicalize_function_name = "lexicalize_" + msg_name
            random_title = random_variation(title_variations)
            lxed_phrses.append(
                eval(lexicalize_function_name)(msg,
                                               lexicalized_title=random_title))
    return lxed_phrses

    
def lexicalize_lastbook_match(lastbook_match_message_block):
    r"""
    lexicalize all the messages contained in a lastbook_match message block
    (aka C{Message})

    @type: C{Message}
    @param: a message (of type "lastbook_match")
    
    @rtype: C{List} of C{Diamond}s
    @return: a list of lexicalized phrases, which can be realized with
    I{tccg} directly or turned into sentences beforehand with C{lexicalization.phrase2sentence} to remove ambiguity
    
    possible: sowohl X als auch Y / beide Bücher
    implemented: beide Bücher

    TODO: implement lexicalize_pagerange
    """
    assert lastbook_match_message_block[Feature("msgType")] == "lastbook_match"
    
    msg_block = deepcopy(lastbook_match_message_block)

    num = gen_num("plur")
    art = gen_art("quantbeide")
    agens = create_diamond("AGENS", "artefaktum", "Buch", [num, art])

    lxed_phrses = []
    for msg_name, msg in msg_block.items():
        if isinstance(msg_name, str) and msg_name not in ("lastbook_authors",
                                                          "lastbook_title",
                                                          "pagerange"):
            lexicalize_function_name = "lexicalize_" + msg_name
            lxed_phrses.append(
                eval(lexicalize_function_name)(msg,
                                               lexicalized_title=agens))
    return lxed_phrses


def lexicalize_lastbook_nomatch(lastbook_nomatch_message_block):
    r"""
    Im Gegensatz zum ersten / vorhergehenden / anderen Buch ____
    """
    raise NotImplementedError, "The grammar fragment can't handle lastbook non-matches, yet."

def lexicalize_usermodel_match(usermodel_match_message_block):
    r"""erfüllt Anforderungen / entspricht ihren Wünschen"""
    raise NotImplementedError, "The grammar fragment can't handle usermodel matches, yet."

def lexicalize_usermodel_nomatch(usermodel_nomatch_message_block):
    r"""erfüllt (leider) Anforderungen nicht / entspricht nicht ihren
    Wünschen"""
    raise NotImplementedError, "The grammar fragment can't handle usermodel non-matches, yet."


def random_variation(lexicalization_dictionary):
    """
    @type lexicalization_dictionary: C{Dict}
    @param lexicalization_dictionary: a dictonary, where each key holds the
    name of a message and the value holds the corresponding C{Message}
    @rtype: a randomly chosen value from the given dictionary
    """
    return random.choice(lexicalization_dictionary.values())
