#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Arne Neumann <arne-neumann@web.de>

"""
This module shall convert C{TextPlan}s into HLDS XML structures which can
be utilized by the OpenCCG surface realizer to produce natural language text.
"""

import re
import random
from nltk.featstruct import Feature
from textplan import ConstituentSet, Message, linearize_textplan
from hlds import Diamond, create_diamond, add_mode_suffix
from util import ensure_unicode, sql_array_to_list
from realization import realize as realizer #TODO: dbg, mv to main


def lexicalize_authors(authors, realize="abstract"):
    """
    converts a list of authors into several possible HLDS diamond
    structures, which can be used for text generation.

    @type name: C{list} of C{str}
    @param name: list of names, e.g. ["Ronald Hausser", 
    "Christopher D. Manning"]
    
    @type realize: C{str}
    @param realize: "abstract", "lastnames", "complete". 
    "abstract" realizes 'das Buch' / 'die Bücher'. "lastnames" realizes 
    only the last names of authors, while "complete" realizes their given 
    and last names.

    @rtype: C{Diamond}
    @return: a Diamond instance, which generates "der Autor"/"die Autoren", 
    the authors last names or the complete names of the authors.

    realize one author abstractly:
    >>> realizer(lexicalize_authors(['author1'], realize='abstract'))
    ['dem Autoren', 'den Autoren', 'der Autor', 'des Autors']

    realize two authors abstractly:
    >>> realizer(lexicalize_authors(['author1', 'author2'], realize='abstract'))
    ['den Autoren', 'der Autoren', 'die Autoren']

    realize two authors, only using their lastnames:
    >>> realizer(lexicalize_authors(['Christopher D. Manning', 'Detlef Peter Zaun'], realize='lastnames'))
    ['Manning und Zaun', 'Mannings und Zauns']

    realize two authors using their full names:
    >>> realizer(lexicalize_authors(['Christopher D. Manning', 'Detlef Peter Zaun'], realize='complete'))
    ['Christopher D. Manning und Detlef Peter Zaun', 'Christopher D. Mannings und Detlef Peter Zauns']
    """
    assert isinstance(authors, list), "needs a list of name strings as input"
    assert realize in ("abstract", "lastnames", "complete"), \
        "choose 1 of these author realizations: abstract, lastnames, complete"

    if realize == "abstract":
        num_of_authors = len(authors)
        authors_diamond = gen_abstract_autor(num_of_authors)

    elif realize == "lastnames":
        lastnames = []
        for author in authors:
            lastnames.append(gen_lastname_only(author))
        authors_diamond = gen_enumeration(lastnames, mode="NP")
        
    elif realize == "complete":
        complete_names = []
        for author in authors:
            complete_names.append(gen_complete_name(author))
        authors_diamond = gen_enumeration(complete_names, mode="NP")

    add_mode_suffix(authors_diamond, mode="NP")
    add_mode_suffix(authors_diamond, mode="N")
    return authors_diamond



#TODO: finish writing function lexicalize_authors_examples
def lexicalize_authors_examples(examples, lexicalized_authors, 
                                lexicalized_plang=None, lexeme="verwenden"):
    """
    'der Autor stellt Code-Beispiele in der Programmiersprache X vor'
    'der Autor verwendet keine Code-Beispiele'
    'die Autoren verwenden die Programmiersprache Y für ihre Code-Beispiele'
    """
    temp = gen_tempus("präs")
    agens = lexicalized_authors
    agens.change_mode("AGENS")

    modifier = lexicalized_plang
    preposition = gen_prep("in", "zusammenhang")
    modifier.insert_subdiamond(1, preposition)
    modifier.change_mode("ATTRIB")

    if lexeme == "vorstellen" and lexicalized_plang:
        patiens = create_diamond("PATIENS", "abstraktum", "Code-Beispiel",
                                 [gen_num("plur"), modifier])
        aux = create_diamond("AUX", "partverbstamm", "vor-stellen", 
                             [temp, agens, patiens])
        return create_diamond("", "infinitum", "vor-X-trans", [aux])

    elif lexeme == "verwenden":
        if lexicalized_plang:
            num = gen_num("plur")
            prep = gen_prep("für", "erhalt")
            attrib = create_diamond("ATTRIB", "abstraktum", "Code-Beispiel", 
                                    [num, prep, art])
            patiens = lexicalized_plang
            patiens.append_subdiamond(attrib, mode="ATTRIB")
            return create_diamond("", "handlung", "verwenden", 
                                  [temp, agens, patiens])
            
        else: #enthält keine Code-Beispiele
            #~ modifier = gen_art("quantkein")
            pass
            

#TODO: merge lexicalize_author_examples and lex_title_examples
def lexicalize_title_examples(examples, lexicalized_title, 
                              lexicalized_plang=None, lexeme="enthalten"):
    """
    das Buch enthält Code-Beispiele in den Programmiersprachen A und B.
    „On Syntax“ beinhaltet keine Code-Beispiele. 
    
    @type examples: C{int} or C{str}
    @type lexicalized_title: C{Diamond}
    @type lexicalized_plang: C{Diamond} or C{NoneType}
    
    @type lexeme: C{str}
    @param lexeme: "beinhalten" or "enthalten".
    """
    if isinstance(examples, int):
        examples = str(examples)
        
    temp = gen_tempus("präs")
    agens = lexicalized_title
    agens.change_mode("AGENS")

    if lexicalized_plang: #enthält Code-Bsp. in der Prog.sprache X
        modifier = lexicalized_plang
        preposition = gen_prep("in", "zusammenhang")
        modifier.insert_subdiamond(1, preposition)
        modifier.change_mode("ATTRIB")
    else: #enthält keine Code-Beispiele
        modifier = gen_art("quantkein")
            
    patiens = create_diamond("PATIENS", "abstraktum", "Code-Beispiel",
                             [gen_num("plur"), modifier])
    return create_diamond("", "durativ", lexeme, [temp, agens, patiens])


    
    #~ if lexeme in ("beinhalten", "enthalten", "verwenden"):
        #~ if lexicalized_plang: #enthält Code-Bsp. in der Prog.sprache X
            #~ modifier = lexicalized_plang
            #~ preposition = gen_prep("in", "zusammenhang")
            #~ modifier.insert_subdiamond(1, preposition)
            #~ modifier.change_mode("ATTRIB")
        #~ else: #enthält keine Code-Beispiele
            #~ modifier = gen_art("quantkein")
            #~ 
        #~ patiens = create_diamond(example_mode, example_nom, example_prop,
                                 #~ [example_num, modifier])
        #~ return create_diamond("", "durativ", lexeme, [temp, agens, patiens])
#~ 
    #~ elif lexeme == "vorstellen":
        #~ if lexicalized_plang:
            #~ modifier = lexicalized_plang
            #~ preposition = gen_prep("in", "zusammenhang")
            #~ modifier.insert_subdiamond(1, preposition)
            #~ modifier.change_mode("ATTRIB")
        #~ else: #enthält keine Code-Beispiele
            #~ modifier = gen_art("quantkein")
#~ 
        #~ patiens = create_diamond(example_mode, example_nom, example_prop,
                                 #~ [example_num, modifier])
        #~ aux = create_diamond("AUX", "partverbstamm", "vor-stellen", 
                             #~ [temp, agens, patiens])
        #~ return create_diamond("", "infinitum", "vor-X-trans", [aux])



def lexicalize_keywords(keywords, lexicalized_title=None, 
                        lexicalized_authors = None, realize="abstract", 
                        lexeme="behandeln"):
    r"""
    @type keywords: C{frozenset} of C{str}

    @type realize: C{str}
    @param realize: "abstract", "complete". 
    "abstract" realizes 'das Thema' / 'die Themen'. 
    "complete" realizes an enumeration of those keywords.

    realize one keyword abstractly, using an abstract author and the lexeme
    I{behandeln}:
    
    >>> author = lexicalize_authors(["author1"], realize="abstract")
    >>> realizer(lexicalize_keywords(["keyword1"], lexicalized_authors=author, realize="abstract", lexeme="behandeln"))
    ['behandelt der Autor das Thema', 'der Autor behandelt das Thema', 'der Autor das Thema behandelt']

    realize one keyword concretely, using two concrete authors and the lexeme
    I{beschreiben}:
    
    >>> authors = lexicalize_authors(["John E. Hopcroft","Jeffrey D. Ullman"], realize="complete")
    >>> realizer(lexicalize_keywords(["parsing", "formal languages"], lexicalized_authors=authors, realize="complete", lexeme="beschreiben"))
    ['John E. Hopcroft und Jeffrey D. Ullman beschreiben die Themen parsing und formal_languages', 'John E. Hopcroft und Jeffrey D. Ullman die Themen parsing und formal_languages beschreiben', 'beschreiben John E. Hopcroft und Jeffrey D. Ullman die Themen parsing und formal_languages']

    realize 4 keywords, using 1 author's last name and the lexeme I{eingehen}:
    
    >>> author = lexicalize_authors(["Ralph Grishman"], realize="lastnames")
    >>> realizer(lexicalize_keywords(["parsing","semantics","discourse","generation"], lexicalized_authors=author, realize="complete", lexeme="eingehen"))
    ['Grishman geht auf den Themen parsing , semantics , discourse und generation ein', 'Grishman geht auf die Themen parsing , semantics , discourse und generation ein', 'geht Grishman auf den Themen parsing , semantics , discourse und generation ein', 'geht Grishman auf die Themen parsing , semantics , discourse und generation ein']

    TODO: "___ geht auf den Themen ein" is not OK

    realize 1 keyword, using an abstract book title and the lexeme
    I{aufgreifen}:
    
    >>> title = lexicalize_titles(["book1"], realize="abstract")
    >>> realizer(lexicalize_keywords(["regular expressions"], lexicalized_title=title, realize="complete", lexeme="aufgreifen"))
    ['das Buch greift das Thema regular_expressions auf', 'greift das Buch das Thema regular_expressions auf']

    realize 2 keywords, using a concrete book title and the lexeme
    I{beschreiben}:
    
    >>> title = lexicalize_titles(["Grundlagen der Computerlinguistik"], realize="complete")
    >>> realizer(lexicalize_keywords(["grammar", "corpora"], lexicalized_title=title, realize="complete", lexeme="beschreiben"))
    ['beschreibt \xe2\x80\x9e Grundlagen_der_Computerlinguistik \xe2\x80\x9c die Themen grammar und corpora', '\xe2\x80\x9e Grundlagen_der_Computerlinguistik \xe2\x80\x9c beschreibt die Themen grammar und corpora', '\xe2\x80\x9e Grundlagen_der_Computerlinguistik \xe2\x80\x9c die Themen grammar und corpora beschreibt']
    """
    assert realize in ("abstract", "complete"), \
        "choose 1 of these keyword realizations: abstract, complete"
    num_of_keywords = len(keywords)
    
    if realize == "abstract":
        patiens = gen_abstract_keywords(num_of_keywords)
    elif realize == "complete":
        patiens = gen_keywords(keywords, mode="N")

    patiens.change_mode("PATIENS")

    assert lexicalized_authors or lexicalized_title, \
        "keywords need a lexicalized title or author(s) to be realized"
    
    if lexicalized_title:
        agens = lexicalized_title
    elif lexicalized_authors:
        agens = lexicalized_authors
    
    agens.change_mode("AGENS")
    temp = gen_tempus("präs")
    
    if lexeme in ("behandeln", "beschreiben"):
        return create_diamond("", "handlung", lexeme, 
                              [temp, agens, patiens])
    elif lexeme == "eingehen":
        preposition = gen_prep("auf", "zusammenhang")
        patiens.insert_subdiamond(1, preposition)
        aux = create_diamond("AUX", "partverbstamm", "ein-gehen", 
                             [temp, agens, patiens])
        return create_diamond("", "infinitum", "ein-X-trans", [aux])
    elif lexeme == "aufgreifen":
        aux = create_diamond("AUX", "partverbstamm", "auf-greifen", 
                             [temp, agens, patiens])
        return create_diamond("", "infinitum", "auf-X-trans", [aux])


def lexicalize_pages(pages, lexicalized_title, lexeme="länge"):
    r"""
    ___ hat einen Umfang von 546 Seiten
    ___ umfasst 546 Seiten
    ___ ist 546 Seiten lang
    
    @type pages: C{str} OR C{int}
    @type title: C{str}
    @type authors: C{list} of C{str} OR C{NoneType}
    @rtype: C{Diamond}

    realize "$title hat einen Umfang von $pages Seiten":
    >>> title = lexicalize_titles(["Natural Language Processing"], realize="complete")
    >>> realizer(lexicalize_pages(600, lexicalized_title=title, lexeme="umfang"))
    ['hat \xe2\x80\x9e Natural_Language_Processing \xe2\x80\x9c einen Umfang von 600 Seiten', '\xe2\x80\x9e Natural_Language_Processing \xe2\x80\x9c einen Umfang von 600 Seiten hat', '\xe2\x80\x9e Natural_Language_Processing \xe2\x80\x9c hat einen Umfang von 600 Seiten']

    realize "$abstracttitle umfasst $pages Seiten"
    >>> title = lexicalize_titles(["title1"], realize="abstract")
    >>> realizer(lexicalize_pages(600, lexicalized_title=title, lexeme="umfassen"))
    ['das Buch 600 Seiten umfasst', 'das Buch umfasst 600 Seiten', 'umfasst das Buch 600 Seiten']

    realize "$abstracttitle ist $pages Seiten lang"
    >>> title = lexicalize_titles(["title1"], realize="abstract")
    >>> realizer(lexicalize_pages(600, lexicalized_title=title, lexeme="länge"))
    ['das Buch 600 Seiten lang ist', 'das Buch ist 600 Seiten lang', 'das Buch ist lange 600 Seiten', 'das Buch lange 600 Seiten ist', 'ist das Buch 600 Seiten lang', 'ist das Buch lange 600 Seiten']
    """
    if isinstance(pages, int):
        pages = str(pages)
    
    tempus = gen_tempus("präs")
    title = lexicalized_title
    title.change_mode("AGENS")
    
    pages_num = gen_num("plur")
    pages_mod = gen_mod(pages, "kardinal")
    pages_nom = "artefaktum"
    pages_prop = "Seite"

    if lexeme == "random":
        lexeme = random.choice(["umfang", "umfassen", "länge"])
    
    if lexeme == "umfang": 
        preposition = gen_prep("von", u"zugehörigkeit")
        attrib = create_diamond("ATTRIB", pages_nom, pages_prop, 
                                [pages_num, preposition, pages_mod])
    
        patiens_num = gen_num("sing")
        art = gen_art("indef")
        patiens = create_diamond("PATIENS", "abstraktum", "Umfang", 
                                 [patiens_num, art, attrib])
        
        return create_diamond("", "durativ", "haben", [tempus, title, patiens])
    
    elif lexeme == "umfassen":
        patiens = create_diamond("PATIENS", pages_nom, pages_prop, 
                                 [pages_num, pages_mod])
        return create_diamond("", "handlung", "umfassen",
                              [tempus, title, patiens])

    elif lexeme == "länge":
        title.change_mode("SUBJ")
        komp_mod = create_diamond("MOD", "eigenschaft", "lang", 
                                  [gen_komp("pos")])
        prkompl = create_diamond("PRKOMPL", pages_nom, pages_prop, 
                                 [pages_num, pages_mod, komp_mod])
        return create_diamond("", u"prädikation", "sein-kop", 
                              [tempus, title, prkompl])



def lexicalize_plang(plang, lexicalized_titles=None, lexicalized_authors=None,
                     realize="embedded"):
    r"""
    @type plang: C{str}
    @param plang: an 'sql string array' containing one or more programming 
    languages, e.g. '[Python]' or '[Lisp][Ruby][C++]'.
    
    @type realize: C{str}
    @param realize: "embedded" or "complete".
    if "embedded", the function will just generate a noun phrase, e.g. "die 
    Programmiersprache Perl". if "complete", it will generate a sentence, 
    e.g. "das Buch verwendet die Programmiersprache(n) X (und Y)" or "der 
    Autor/ die Autoren verwenden die Programmiersprache(n) X (und Y)".

    realize "die Programmiersprachen A, B und C":
    >>> realizer(lexicalize_plang("[Python][Lisp][C++]", realize="embedded"))
    ['den Programmiersprachen Python , Lisp und C++', 'der Programmiersprachen Python , Lisp und C++', 'die Programmiersprachen Python , Lisp und C++']

    realize two authors who use several programming languages:
    >>> authors = lexicalize_authors(["Horst Lohnstein", "Ralf Klabunde"], realize="lastnames")
    >>> realizer(lexicalize_plang("[Python][Lisp][C++]", lexicalized_authors=authors, realize="complete"))
    ['Lohnstein und Klabunde die Programmiersprachen Python , Lisp und C++ verwenden', 'Lohnstein und Klabunde verwenden die Programmiersprachen Python , Lisp und C++', 'verwenden Lohnstein und Klabunde die Programmiersprachen Python , Lisp und C++']

    realize a book title with several programming languages:
    >>> title = lexicalize_titles(["Natural Language Processing"], realize="complete")
    >>> realizer(lexicalize_plang("[Python][Lisp][C++]", lexicalized_titles=title, realize="complete"))
    ['verwendet \xe2\x80\x9e Natural_Language_Processing \xe2\x80\x9c die Programmiersprachen Python , Lisp und C++', '\xe2\x80\x9e Natural_Language_Processing \xe2\x80\x9c die Programmiersprachen Python , Lisp und C++ verwendet', '\xe2\x80\x9e Natural_Language_Processing \xe2\x80\x9c verwendet die Programmiersprachen Python , Lisp und C++']
    """
    assert lexicalized_titles or lexicalized_authors or realize == "embedded", \
        "requires either a lexicalized title, a lexicalized set of authors or"\
        " realize parameter == 'embedded'"
    if realize == "embedded":
        return gen_plang(plang, mode="N")
        #just realize a noun prase, e.g. "die Prog.sprachen A und B"

    elif realize == "complete":
        temp = gen_tempus("präs")
        if lexicalized_titles:
            agens = lexicalized_titles
        elif lexicalized_authors:
            agens = lexicalized_authors
        
        agens.change_mode("AGENS")
        patiens = gen_plang(plang, mode="PATIENS")
        return create_diamond("", "handlung", "verwenden", 
                              [temp, agens, patiens])



def lexicalize_titles(book_titles, lexicalized_authors=None,
                      realize="complete", authors_realize="random"):
    """
    @type book_title: C{list} of C{str}
    @param book_title: list of book title strings
    
    @type lexicalized_authors: C{Diamond} OR C{NoneType}
    @param authors: an I{optional} C{Diamond} containing a lexicalized
    authors message
    
    @type realize: C{str}
    @param realize: "abstract", "complete", "pronoun" or "authors+title" 
    - "abstract" realizes 'das Buch' / 'die Bücher'
    - "pronoun" realizes 'es' / 'sie'
    - "complete" realizes book titles in the format specified in the 
      OpenCC grammar, e.g. „ Computational Linguistics. An Introduction “

    realize one book title abstractly ("das Buch"):
    
    >>> realizer(lexicalize_titles(["foo book"], realize="abstract"))
    ['das Buch', 'dem Buch', 'des Buches']

    realize two book titles abstractly ("die Bücher"):
    
    >>> realizer(lexicalize_titles(["1st book", "2nd book"], realize="abstract"))
    ['den B\xc3\xbcchern', 'der B\xc3\xbccher', 'die B\xc3\xbccher']

    
    """
    assert isinstance(book_titles, list), "needs a list of titles as input"
    assert realize in ("abstract", "complete", "pronoun", "random")
    num_of_titles = len(book_titles)
    
    if realize == "random":
        realize = random.choice(["abstract", "complete", "pronoun"])
        
    if realize == "abstract":
        title_diamond = gen_abstract_title(num_of_titles)
    elif realize == "pronoun":
        title_diamond = gen_personal_pronoun(num_of_titles, "neut", 3)
    else: # realize == "complete"
        realized_titles = []
        for title in book_titles:
            realized_titles.append(gen_title(title))
        titles_enum = gen_enumeration(realized_titles, mode="NP")
        add_mode_suffix(titles_enum, mode="NP")
        title_diamond = titles_enum

    if lexicalized_authors: 
        #~ assert __sing_or_plur(lexicalized_authors) == "sing", \
            #~ "authors+title mode can only realize one book title"

        if authors_realize == "random":
            if __sing_or_plur(lexicalized_authors) == "sing":
                authors_realize = random.choice(["possessive", "preposition"])
            else: # possessive form doesn't work w/ more than one author
                authors_realize = "preposition"
            
        if authors_realize == "possessive": # Chomskys Buch
            assert __sing_or_plur(lexicalized_authors) == "sing", \
                "can't realize possesive form with more than one author"
            title_diamond.append_subdiamond(lexicalized_authors, mode="ASS")

            article = re.compile("\d+__ART")
            # remove ARTicle from title: Chomskys das Buch --> Chomskys Buch
            for key in title_diamond.keys():
                if isinstance(key, str) and article.match(key):
                    article_key = article.match(key).group()
                    title_diamond.pop(article_key)

            
        else: # authors_realize == "preposition": das Buch von Chomsky
            preposition_diamond = gen_prep("von", "zugehörigkeit")
            lexicalized_authors.prepend_subdiamond(preposition_diamond)
            title_diamond.append_subdiamond(lexicalized_authors, mode="ATTRIB")

    return title_diamond
            


def lexicalize_year(year, lexicalized_title):
    """___ ist/sind 1986 erschienen.

    @type year: C{int} or C{str}
    """
    tempus = gen_tempus("imperf")
    adv = create_diamond("ADV", "modus", str(year), [])
    agens = lexicalized_title
    agens[Feature("mode")] = "AGENS"
    
    aux = create_diamond("AUX", "sein", "sein", [tempus, adv, agens])
    return create_diamond("", "inchoativ", "erscheinen", [aux])





    

def gen_enumeration(diamonds_list, mode=""):
    """
    Takes a list of Diamond instances and combines them into a nested Diamond.
    This nested Diamond can be used to generate an enumeration, such as::

        A
        A und B
        A, B und C
        A, B, C und D
        ...

    @type diamonds_list: C{list} of C{Diamond}s

    @rtype: C{Diamond}
    @return: a Diamond instance (containing zero or more nested Diamond
    instances)
    """
    if len(diamonds_list) is 0:
        return []
    if len(diamonds_list) is 1:
        return diamonds_list[0]
    if len(diamonds_list) is 2:
        return create_diamond(mode, "konjunktion", "und", diamonds_list)
    if len(diamonds_list) > 2:
        nested_komma_enum = gen_komma_enumeration(diamonds_list[:-1], mode)
        return create_diamond(mode, "konjunktion", "und", 
                              [nested_komma_enum, diamonds_list[-1]])


def gen_komma_enumeration(diamonds_list, mode=""):
    """
    This function will be called by gen_enumeration() and takes a list of
    Diamond instances and combines them into a nested Diamond, expressing comma
    separated items, e.g.:

        Manning, Chomsky
        Manning, Chomsky, Allen
        ...

    @type diamonds_list: C{list} of C{Diamond}s

    @rtype: C{Diamond}
    @return: a Diamond instance (containing zero or more nested Diamond
    instances)
    """
    if len(diamonds_list) == 0:
        return []
    if len(diamonds_list) == 1:
        return diamonds_list[0]
    if len(diamonds_list) == 2:
        return create_diamond(mode, "konjunktion", "komma", diamonds_list)
    if len(diamonds_list) > 2:
        nested_komma_enum = gen_komma_enumeration(diamonds_list[:-1], mode)
        return create_diamond(mode, "konjunktion", "komma",
                              [nested_komma_enum, diamonds_list[-1]])


def __split_name(name):
    """
    naively splits a name string into a last name and a given name
    (or given names).

    @type name: C{Str}
    @param name: a name, e.g. "George W. Bush"

    @rtype: C{tuple} of (C{list}, C{str}), where C{list} consists of C{str}s
    @return: a list of given names and a string containing the last name
    """
    name_components = name.split()
    given_names, last_name = name_components[:-1], name_components[-1]
    return given_names, last_name


def gen_nested_given_names(given_names):
    """
    given names are represented as nested (diamond) structures in HLDS
    (instead of using indices to specify the first given name, second given
    name etc.), where the last given name is the outermost structural
    element and the first given name is the innermost one.

    @type given_names: C{list} of C{str}
    @rtype: empty C{list} or C{Diamond}
    @return: returns an empty list if given_names is empty. otherwise returns a
    C{Diamond} (which might contain other diamonds)
    """
    if given_names:
        preceding_names, last_given_name = given_names[:-1], given_names[-1]
        nested_diamond = gen_nested_given_names(preceding_names)

        if type(nested_diamond) is list:
            return create_diamond("N1", "vorname", last_given_name, 
                                  nested_diamond)
        elif type(nested_diamond) is Diamond:
            return create_diamond("N1", "vorname", last_given_name,
                                  [nested_diamond])

    else: # given_names list is empty
        return []


def gen_personal_pronoun(count, gender, person):
    """
    @type count: C{int}
    @param count: 1 for 'singular'; > 1 for 'plural'
    
    @type gender: C{str}
    @param gender: 'masc', 'fem' or 'neut'
    
    @type person: C{int}
    @param person: 1 for 1st person, 2 for 2nd person ...
    """
    if count > 1 or gender == "":
        gender = "fem" # there should be no gender marker in plural, 
                       # but that doesn't always work with ccg-realize, so
                       # we'll always stick to "feminine", which seems to work.
        
    person_prop_str = "{0}te".format(str(person)) # 3 -> 3te
    
    pers = create_diamond("PERS", "", person_prop_str, [])
    pro = create_diamond("PRO", "", "perspro", [])
    gen = gen_gender(gender)
    num = gen_num(count)
    return create_diamond("", "sem-obj", "", [pers, pro, gen, num])


def gen_art(article_type="def"):
    """generates a C{Diamond} describing an article"""
    return create_diamond("ART", "sem-obj", article_type, [])

def gen_gender(genus="mask"):
    """generates a C{Diamond} representing masculine, feminine or neuter"""
    return create_diamond("GEN", "", genus, [])
    
def gen_num(numerus=1):
    """
    generates a C{Diamond} representing singular or plural
    
    @type numerus: C{str} or C{int}
    @param numerus: either a string representing singular or plural 
    ("sing", "plur"), or an integer.
    @rtype: C{Diamond}
    """
    if isinstance(numerus, int):
        assert numerus > 0, "count has to be >= 1"
        if numerus == 1:
            numerus = "sing"
        elif numerus > 1:
            numerus = "plur"

    assert numerus in ("sing", "plur")
    return create_diamond("NUM", "", numerus, [])
    
def gen_mod(modifier, modifier_type="kardinal"):
    """generates a C{Diamond} representing a modifier"""
    return create_diamond("MOD", modifier_type, modifier, [])
    
def gen_prep(preposition, preposition_type="zugehörigkeit"):
    """generates a C{Diamond} representing a preposition"""
    return create_diamond("PRÄP", preposition_type, preposition, [])
    
def gen_pers(person):
    """generates a C{Diamond} representing 1st, 2nd or 3rd person"""
    return create_diamond("PERS", "", "{0}te".format(str(person)), [])

def gen_tempus(tense="präs"):
    """generates a C{Diamond} representing a tense form"""
    return create_diamond("TEMP:tempus", "", tense, [])
    
def gen_komp(modality="komp"):
    """
    generates a C{Diamond} expressing adjective modality, i.e. 'positiv',
    'komperativ' or 'superlativ'.
    """
    assert modality in ("pos", "komp", "super")
    return create_diamond("KOMP", "", modality, [])


def gen_title(book_title):
    """
    Converts a book title (string) into its corresponding HLDS diamond
    structure. Since book titles are hard coded into the grammar, the OpenCCG
    output will differ somewhat, e.g.::

        'Computational Linguistics' --> '„ Computational Linguistics “'

    @type book_title: C{unicode}
    @rtype: C{Diamond}
    """
    book_title = ensure_unicode(book_title)
    book_title = book_title.replace(u" ", u"_")

    opening_bracket = create_diamond('99', u'anf\xfchrung\xf6ffnen',
                                     u'anf\xf6ffn', [])
    closing_bracket = create_diamond('66', u'anf\xfchrungschlie\xdfen',
                                     'anfschl', [])

    return create_diamond('NP', 'buchtitel', book_title, 
                          [opening_bracket, closing_bracket])
    

def gen_abstract_title(number_of_books):
    """
    given an integer representing a number of books returns a Diamond, which
    can be realized as either "das Buch" or "die Bücher"

    @type number_of_books: C{int}
    @rtype: C{Diamond}
    """
    num = gen_num(number_of_books)
    art = gen_art("def")
    return create_diamond("", "artefaktum", "Buch", [num, art])

def gen_abstract_autor(num_of_authors):
    """
    given an integer (number of authors), returns a Diamond instance which
    generates "der Autor" or "die Autoren".

    @type num_of_authors: C{int}
    @param num_of_authors: the number of authors of a book

    @rtype: C{Diamond}
    """
    art = gen_art("def")
    gen = gen_gender("mask")
    num = gen_num(num_of_authors)
    return create_diamond("", u"bel-phys-körper", "Autor", [art, gen, num])



def gen_lastname_only(name):
    """
    given an authors name ("Christopher D. Manning"), the function returns a
    Diamond instance which can be used to realize the author's last name.

    NOTE: This does not work with last names that include whitespace, e.g.
    "du Bois" or "von Neumann".

    @type name: C{str}
    @rtype: C{Diamond}
    """
    _, lastname_str = __split_name(name)
    return create_diamond("NP", "nachname", lastname_str, [])


def gen_complete_name(name):
    """
    takes a name as a string and returns a corresponding nested HLDS diamond
    structure.

    @type name: C{str}
    @rtype: C{Diamond}
    """
    given_names, lastname_str = __split_name(name)
    if given_names:
        given_names_diamond = gen_nested_given_names(given_names)
        return create_diamond("NP", "nachname", lastname_str, 
                              [given_names_diamond])
    else: #if name string does not contain ' ', i.e. only last name is given
        return create_diamond("NP", "nachname", lastname_str, [])


def gen_abstract_keywords(num_of_keywords):
    """generates a Diamond for 'das Thema' vs. 'die Themen' """
    num = gen_num(num_of_keywords)
    art = gen_art("def")
    return create_diamond("", "art", "Thema", [num, art])


def gen_keywords(keywords, mode="N"):
    """
    takes a list of keyword (strings) and converts them into a nested
    C{Diamond} structure and prepends "das Thema" or "die Themen"

    @type keywords: C{list} of C{str}
    @rtype: C{Diamond}
    """
    assert isinstance(keywords, list), "input needs to be a list"

    num_of_keywords = len(keywords)
    keyword_description = gen_abstract_keywords(num_of_keywords)
    
    def gen_keyword(keyword, mode):
        """takes a keyword (string) and converts it into a C{Diamond}"""
        fixed_keyword = keyword.replace(" ", "_")
        num = gen_num("sing")
        return create_diamond(mode, "sorte", fixed_keyword, [num])

    if isinstance(keywords, list) and len(keywords) == 1:
        result_diamond = gen_keyword(keywords[0], mode)

    elif isinstance(keywords, list) and len(keywords) > 1:
        keyword_diamonds = [gen_keyword(kw, mode) for kw in keywords]
        result_diamond = gen_enumeration(keyword_diamonds, mode)
        
    keyword_description.append_subdiamond(result_diamond, mode="NOMERG")    
    add_mode_suffix(keyword_description, mode)
    return keyword_description

def gen_plang(plang, mode=""):
    """
    generates a C{Diamond} representing programming languages, e.g. 'die Programmiersprache X' or 'die Programmiersprachen X und Y'.
    
    @type plang: C{str}
    @param plang: an 'sql string array' containing one or more programming 
    languages, e.g. '[Python]' or '[Lisp][Ruby][C++]'.
    
    @type mode: C{str}
    @param mode: sets the mode attribute of the resulting C{Diamond}
    
    @rtype: C{Diamond}
    """
    assert plang, "at least one programming language should be defined"
    proglangs = sql_array_to_list(plang)
    num_of_proglangs = len(proglangs)

    num = gen_num(num_of_proglangs)
    art = gen_art("def")

    proglang_diamonds = []
    for proglang in proglangs:
        proglang_diamonds.append(create_diamond("N", "sorte", proglang, 
                                 [gen_num("sing")]))

    proglang_enum = gen_enumeration(proglang_diamonds, mode="N")
    proglang_enum.change_mode("NOMERG")
    add_mode_suffix(proglang_enum, mode="N")
    
    return create_diamond(mode, "art", "Programmiersprache", 
                         [num, art, proglang_enum])


def __sing_or_plur(lexicalized_authors):
    """
    does is lexicalized authors diamond describe one or more authors?
    
    @type lexicalized_authors: C{Diamond}
    
    @rtype: C{str}
    @return: "sing" or "plur"
    """
    if lexicalized_authors["prop"] == "und": # if realized as "lastnames"
                                             # or "complete" 
        return "plur"
    elif "02__NUM" in lexicalized_authors: # if realized as "abstract"
        return lexicalized_authors["02__NUM"]["prop"]
    else:
        return "sing"

