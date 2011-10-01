#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Arne Neumann <arne-neumann@web.de>

"""
This module contains all functions that are necessary to evaluate the 
lexicalization process.
"""

from lexicalization import *

def test_keywords():
    """
    retrieves all sets of keywords from the database and realizes them with
    I{ccg-realize}.
    """
    keyword_lists = [["parsing"],
                     ["statistics","corpus linguistics"],
                     ["left associative grammar", "chart parsing", "semantics", "pragmatics"]]

    for keyword_list in keyword_lists:
        lexicalized_keywords = lexicalize_keywords(keyword_list, 
                                                   realize="complete")
        print "Die Themenliste: {0}".format(keyword_list)
        print "wird generiert als:\n"
        printeach(realize(lexicalized_keywords))
        print "\n\n"


def test_authors():
    """
    realizes three sets of authors with I{ccg-realize}.
    """
    author_lists = [[u'Detlef Peter Zaun'],
                    [u'Fernando C. N. Pereira', u'Barbara J. Grosz'],
                    [u'Peter Norvig', u'Martin Kay', u'Jean Mark Gawron']]
    
    for author_list in author_lists:
        lexicalized_authors = lexicalize_authors(author_list, 
                                                 realize="complete")
        print "Die Autorenliste: {0}".format(author_list)
        print "wird generiert als:\n"
        printeach(realize(lexicalized_authors))
        print "\n\n"


def test_titles():
    """
    retrieves all book titles and realizes 3 random combinations of these with
    I{ccg-realize}.
    """
    print "realize one book abstractly:"
    print realize(lexicalize_titles(["some book"], realize="abstract")), "\n\n"
    
    print "realize two books abstractly:"
    print realize(lexicalize_titles(["some book", "another book"], 
                                    realize="abstract")), "\n\n"

    print "realize one book abstractly (as a pronoun):"
    print realize(lexicalize_titles(["some book"], realize="pronoun")), "\n\n"
    
    # TODO: realized wrongly ("ihnen" instead of "sie")
    print "realize two books abstractly: (as a pronoun)"
    print realize(lexicalize_titles(["some book", "another book"], 
                                    realize="pronoun")), "\n\n"

    print "realize one book abstractly with an author:"
    print realize(lexicalize_titles(["some book"], ["Christopher D. Manning"], 
                                    realize="abstract")), "\n\n"
    
    print "realize one book abstractly with two authors:"
    print realize(lexicalize_titles(["some book"], 
                                    ["Christopher D. Manning", "Alan Davies"], 
                                    realize="abstract")), "\n\n"

    print "realize one book concretely:"
    print realize(lexicalize_titles(["Natural Language Processing"], 
                                    realize="complete")), "\n\n"

    print "realize two books concretely:"
    print realize(lexicalize_titles(["Text Processing in Python", 
                                     "Natural Language Processing"], 
                                    realize="complete")), "\n\n"

    print "realize one book concretely with one author (possessive):"
    print realize(lexicalize_titles(["Natural Language Understanding"],
                                    ["James Allen"],
                                    realize="complete",
                                    authors_realize="possessive")), "\n\n"
    
    print "realize one book concretely with one author (preposition):"
    print realize(lexicalize_titles(["Natural Language Understanding"],
                                    ["James Allen"],
                                    realize="complete",
                                    authors_realize="preposition")), "\n\n"
    
    print "realize one book concretely with two authors (preposition):"
    print realize(lexicalize_titles(["Einführung in die Automatentheorie, Formale Sprachen und Komplexitätstheorie"],
                                    ["John E. Hopcroft", "Jeffrey D. Ullman"],
                                    realize="complete",
                                    authors_realize="preposition")), "\n\n"

def printeach(iterable):
    for item in iterable:
        print item
