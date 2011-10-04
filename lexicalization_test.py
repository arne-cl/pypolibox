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
    realizes three sets of keywords with I{ccg-realize}.
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
    realizes three sets of authors with I{ccg-realize}. there are realized 
    as an enumeration of full names, an enumeration of last names as well 
    as abstractly ("der Autor", "die Autoren").
    """
    author_lists = [[u'Detlef Peter Zaun'],
                    [u'Fernando C. N. Pereira', u'Barbara J. Grosz'],
                    [u'Peter Norvig', u'Martin Kay', u'Jean Mark Gawron']]
    
    for author_list in author_lists:
        lexicalized_authors = lexicalize_authors(author_list, 
                                                 realize="complete")
        print "Die Autorenliste: {0}".format(author_list)
        print "wird mit vollständigen Namen generiert als:\n"
        printeach(realize(lexicalized_authors))
        print "\n\n"

    for author_list in author_lists:
        lexicalized_authors = lexicalize_authors(author_list, 
                                                 realize="lastnames")
        print "Die Autorenliste: {0}".format(author_list)
        print "wird als Nachnamenliste so generiert:\n"
        printeach(realize(lexicalized_authors))
        print "\n\n"

    for author_list in author_lists:
        lexicalized_authors = lexicalize_authors(author_list, 
                                                 realize="abstract")
        print "Die Autorenliste: {0}".format(author_list)
        print "wird abstrahiert generiert als:\n"
        printeach(realize(lexicalized_authors))
        print "\n\n"


def test_titles():
    """
    retrieves all book titles and realizes 3 random combinations of these with
    I{ccg-realize}.
    """
    print "realize one book abstractly:"
    printeach(realize(lexicalize_titles(["some book"], realize="abstract")))
    
    print "\n\n", "realize two books abstractly:"
    printeach(realize(lexicalize_titles(["some book", "another book"], 
                                        realize="abstract")))

    print "\n\n", "realize one book abstractly (as a pronoun):"
    printeach(realize(lexicalize_titles(["some book"], realize="pronoun")))
    
    # TODO: realized wrongly ("ihnen" instead of "sie")
    print "\n\n", "realize two books abstractly: (as a pronoun)"
    printeach(realize(lexicalize_titles(["some book", "another book"], 
                                        realize="pronoun")))

    print "\n\n", "realize one book abstractly with an author:"
    printeach(realize(lexicalize_titles(["some book"], 
                                        ["Christopher D. Manning"], 
                                        realize="abstract")))
    
    print "\n\n", "realize one book abstractly with two authors:"
    printeach(realize(lexicalize_titles(["some book"], 
                                        ["Christopher D. Manning", 
                                         "Alan Davies"], 
                                        realize="abstract")))

    print "\n\n", "realize one book concretely:"
    printeach(realize(lexicalize_titles(["Natural Language Processing"], 
                                    realize="complete")))

    print "\n\n", "realize two books concretely:"
    printeach(realize(lexicalize_titles(["Text Processing in Python", 
                                     "Natural Language Processing"], 
                                    realize="complete")))

    print "\n\n", "realize one book concretely with one author (possessive):"
    printeach(realize(lexicalize_titles(["Natural Language Understanding"],
                                        ["James Allen"],
                                        realize="complete",
                                        authors_realize="possessive")))
    
    print "\n\n", "realize one book concretely with one author (preposition):"
    printeach(realize(lexicalize_titles(["Natural Language Understanding"],
                                        ["James Allen"],
                                        realize="complete",
                                        authors_realize="preposition")))
    
    print "\n\n", "realize one book concretely with two authors (preposition):"
    printeach(realize(lexicalize_titles(["Einführung in die Automatentheorie, Formale Sprachen und Komplexitätstheorie"],
                                    ["John E. Hopcroft", "Jeffrey D. Ullman"],
                                    realize="complete",
                                    authors_realize="preposition")))


def test_pages():
    """
    realizes some instances of:
    $title hat einen Umfang von $pages Seiten
    """
    print "realize one book title abstractly with its number of pages:"
    printeach(realize(lexicalize_pages("193", 
                                       "random book title", 
                                       title_realize="abstract")))

    print "\n\n", "realize one book title abstractly (pronoun) " \
          "with its number of pages:"
    printeach(realize(lexicalize_pages("193", 
                                       "random book title", 
                                       title_realize="pronoun")))
                                       
    print "\n\n", "realize one book title concretely with its number of pages:"
    printeach(realize(lexicalize_pages("193", 
                                 "Computational Linguistics. An Introduction.", 
                                       title_realize="complete")))
    
    
    

def printeach(iterable):
    """prints each element of an iterable on a separate line"""
    for item in iterable:
        print item
