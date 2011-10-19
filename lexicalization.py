#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Arne Neumann <arne-neumann@web.de>

"""
This module shall convert C{TextPlan}s into HLDS XML structures which can
be utilized by the OpenCCG surface realizer to produce natural language text.
"""

import random
from nltk.featstruct import Feature
from textplan import ConstituentSet, Message
from hlds import Diamond, create_diamond, add_mode_suffix
from util import ensure_unicode, sql_array_to_list


def linearize_textplan(textplan): #TODO: add better explanation to docstring
    """
    takes a text plan (an RST tree represented as a NLTK.featstruct data
    structure) and returns an ordered list of constituent sets (RST
    relations that combine two messages).

    @type textplan: C{TextPlan}
    @param textplan: a complete text plan (RST tree) encoded as a feature
    structure

    @rtype: C{list} of C{ConstituentSet}s
    @return: a list of constituent sets in the order they should be realized by
    surface generation
    """
    rstree = textplan["children"] # we don't need to process the title/metadata
    if type(rstree) is Message:
        # if the text plan just consists of one message, return it
        return rstree

    start = 0
    rst_list = __rstree2list(rstree)
    #~ if not rst_list:
        #~ return []

    for i in range(len(rst_list)-1):
    # we're looking for the first element of the list that is the nucleus of
    # its successor.
        if rst_list[i] is not rst_list[i+1][Feature("nucleus")]:
            pass
        else:
            start = i
            break

    linearized_structures = []
    linearized_structures.append(rst_list[start])

    rest = rst_list[start+1:]
    # if rst_list contains only one element, this loop won't be executed at all
    for i, fstruct in enumerate(rest):
        if type(fstruct[Feature("satellite")]) is Message:
            structure = ConstituentSet(relType=fstruct[Feature("relType")],
                                       satellite=fstruct[Feature("satellite")])
            linearized_structures.append(structure)

        elif type(fstruct[Feature("satellite")]) is ConstituentSet:
        # if the satellite is nested further
            structure = ConstituentSet(relType=fstruct[Feature("relType")])
            linearized_structures.append(structure)

            nested_structure = fstruct[Feature("satellite")]
            linearized_structures.append(nested_structure)
    return linearized_structures


def __rstree2list(featstruct):
    """
    walks through a feature structure (RST tree) and returns a list of
    constituent sets in the order of a depth-first search. a constituent
    set consists of one RST relation that combines two message blocks (here
    called nucleus and satellite).
    """
    rst_list = [fs for fs in featstruct.walk() if type(fs) is ConstituentSet]
    rst_list.reverse()
    return rst_list


def lexicalize_titles(book_titles, authors=None, realize="complete", 
                      authors_realize="random"):
    """
    @type book_title: C{list} of C{str}
    @param book_title: list of book title strings
    
    @type authors: C{list} of C{str} OR C{NoneType}
    @param authors: an I{optional} list of author names
    
    @type realize: C{str}
    @param realize: "abstract", "complete", "pronoun" or "authors+title" 
    - "abstract" realizes 'das Buch' / 'die Bücher'
    - "pronoun" realizes 'es' / 'sie'
    - "complete" realizes book titles in the format specified in the 
      OpenCC grammar, e.g. „ Computational Linguistics. An Introduction “
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
        titles_enum = __gen_enumeration(realized_titles, mode="NP")
        add_mode_suffix(titles_enum, mode="NP")
        title_diamond = titles_enum

    if authors: 
        assert isinstance(authors, list), \
            "authors+title mode needs a non-empty list of authors as input"
        assert num_of_titles == 1, \
            "authors+title mode can only realize one book title"

        authors_diamond = lexicalize_authors(authors, realize="complete")

        if authors_realize == "random":
            if len(authors) == 1:
                authors_realize = random.choice(["possessive", "preposition"])
            else: # possessive form doesn't work w/ more than one author
                authors_realize = "preposition"
            
        if authors_realize == "possessive": # Chomskys Buch
            assert len(authors) == 1, \
                "can't realize possesive form with more than one author"
            title_diamond.append_subdiamond(authors_diamond, mode="ASS")
        else: # authors_realize == "preposition": das Buch von Chomsky
            preposition_diamond = gen_prep("von", "zugehörigkeit")
            authors_diamond.prepend_subdiamond(preposition_diamond)
            title_diamond.append_subdiamond(authors_diamond, mode="ATTRIB")

    return title_diamond
            
            
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
    """
    assert isinstance(authors, list), "needs a list of name strings as input"
    assert realize in ("abstract", "lastnames", "complete"), \
        "choose 1 of these author realizations: abstract, lastnames, complete"

    if realize == "abstract":
        num_of_authors = len(authors)
        authors_diamond = __gen_abstract_autor(num_of_authors)

    elif realize == "lastnames":
        lastnames = []
        for author in authors:
            lastnames.append(__gen_lastname_only(author))
        authors_diamond = __gen_enumeration(lastnames, mode="NP")
        
    elif realize == "complete":
        complete_names = []
        for author in authors:
            complete_names.append(__gen_complete_name(author))
        authors_diamond = __gen_enumeration(complete_names, mode="NP")

    add_mode_suffix(authors_diamond, mode="NP")
    add_mode_suffix(authors_diamond, mode="N")
    return authors_diamond


def __gen_abstract_autor(num_of_authors):
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



def __gen_lastname_only(name):
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


def __gen_complete_name(name):
    """
    takes a name as a string and returns a corresponding nested HLDS diamond
    structure.

    @type name: C{str}
    @rtype: C{Diamond}
    """
    given_names, lastname_str = __split_name(name)
    if given_names:
        given_names_diamond = __create_nested_given_names(given_names)
        return create_diamond("NP", "nachname", lastname_str, 
                              [given_names_diamond])
    else: #if name string does not contain ' ', i.e. only last name is given
        return create_diamond("NP", "nachname", lastname_str, [])


def lexicalize_keywords(keywords, lexicalized_title=None, 
                        lexicalized_authors = None, realize="abstract", 
                        lexeme="behandeln"):
    """
    @type keywords: C{frozenset} of C{str}

    @type realize: C{str}
    @param realize: "abstract", "complete". 
    "abstract" realizes 'das Thema' / 'die Themen'. 
    "complete" realizes an enumeration of those keywords.
    """
    assert realize in ("abstract", "complete"), \
        "choose 1 of these keyword realizations: abstract, complete"
    num_of_keywords = len(keywords)
    
    if realize == "abstract":
        patiens = __gen_abstract_keywords(num_of_keywords)
    elif realize == "complete":
        patiens = __gen_keywords(keywords, mode="N")

    patiens.change_mode("PATIENS")
    
    if lexicalized_title and isinstance(lexicalized_title, Diamond):
        agens = lexicalized_title
    elif lexicalized_authors and isinstance(lexicalized_authors, Diamond):
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

def __gen_abstract_keywords(num_of_keywords):
    """generates a Diamond for 'das Thema' vs. 'die Themen' """
    num = gen_num(num_of_keywords)
    art = gen_art("def")
    return create_diamond("", "art", "Thema", [num, art])


def __gen_keywords(keywords, mode="N"):
    """
    takes a list of keyword (strings) and converts them into a nested
    C{Diamond} structure and prepends "das Thema" or "die Themen"

    @type keywords: C{list} of C{str}
    @rtype: C{Diamond}
    """
    assert isinstance(keywords, list), "input needs to be a list"

    num_of_keywords = len(keywords)
    keyword_description = __gen_abstract_keywords(num_of_keywords)
    
    def gen_keyword(keyword, mode):
        """takes a keyword (string) and converts it into a C{Diamond}"""
        fixed_keyword = keyword.replace(" ", "_")
        num = gen_num("sing")
        return create_diamond(mode, "sorte", fixed_keyword, [num])

    if isinstance(keywords, list) and len(keywords) == 1:
        result_diamond = gen_keyword(keywords[0], mode)

    elif isinstance(keywords, list) and len(keywords) > 1:
        keyword_diamonds = [gen_keyword(kw, mode) for kw in keywords]
        result_diamond = __gen_enumeration(keyword_diamonds, mode)
        
    keyword_description.append_subdiamond(result_diamond, mode="NOMERG")    
    add_mode_suffix(keyword_description, mode)
    return keyword_description
    


#TODO: lexicalize_year(): authors should be args*
def lexicalize_year(year, title, realize="complete"):
    """___ ist 1986 erschienen.
    """
    tempus = gen_tempus("imperf")
    adv = create_diamond("ADV", "modus", year, [])
    agens = lexicalize_titles(title, realize=realize)
    agens[Feature("mode")] = "AGENS"
    
    aux = create_diamond("AUX", "sein", "sein", [tempus, adv, agens])
    return create_diamond("", "inchoativ", "erscheinen", [aux])



def lexicalize_pages(pages, lexicalized_title, lexeme="länge"):
    """
    ___ hat einen Umfang von 546 Seiten
    ___ umfasst 546 Seiten
    ___ ist 546 Seiten lang
    
    @type pages: C{str} OR C{int}
    @type title: C{str}
    @type authors: C{list} of C{str} OR C{NoneType}
    
    @type title_realize: C{str}
    @param title_realize: "abstract", "pronoun" or "complete".
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



def lexicalize_plang(plang, lexicalized_title=None, lexicalized_authors=None,
                     realize="embedded"):
    """
    @type plang: C{str}
    @param plang: an 'sql string array' containing one or more programming 
    languages, e.g. '[Python]' or '[Lisp][Ruby][C++]'.
    
    @type realize: C{str}
    @param realize: "embedded" or "complete".
    if "embedded", the function will just generate a noun phrase, e.g. "die 
    Programmiersprache Perl". if "complete", it will generate a sentence, 
    e.g. "das Buch verwendet die Programmiersprache(n) X (und Y)" or "der 
    Autor/ die Autoren verwenden die Programmiersprache(n) X (und Y)".
    """
    assert lexicalized_title or lexicalized_authors or realize == "embedded", \
        "requires either a lexicalized title, a lexicalized set of authors or"\
        "realize parameter == 'embedded'"
    if realize == "embedded":
        return __gen_plang(plang, mode="N")
        #just realize a noun prase, e.g. "die Prog.sprachen A und B"

    elif realize == "complete":
        temp = gen_tempus("präs")
        if lexicalized_title:
            agens = lexicalized_title
        elif lexicalized_authors:
            agens = lexicalized_authors
        
        agens.change_mode("AGENS")
        patiens = __gen_plang(plang, mode="PATIENS")
        return create_diamond("", "handlung", "verwenden", 
                              [temp, agens, patiens])


def __gen_plang(plang, mode=""):
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

    proglang_enum = __gen_enumeration(proglang_diamonds, mode="N")
    proglang_enum.change_mode("NOMERG")
    add_mode_suffix(proglang_enum, mode="N")
    
    return create_diamond(mode, "art", "Programmiersprache", 
                         [num, art, proglang_enum])
    

def __gen_enumeration(diamonds_list, mode=""):
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
        nested_komma_enum = __gen_komma_enumeration(diamonds_list[:-1], mode)
        return create_diamond(mode, "konjunktion", "und", 
                              [nested_komma_enum, diamonds_list[-1]])


def __gen_komma_enumeration(diamonds_list, mode=""):
    """
    This function will be called by __gen_enumeration() and takes a list of
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
        nested_komma_enum = __gen_komma_enumeration(diamonds_list[:-1], mode)
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


def __create_nested_given_names(given_names):
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
        nested_diamond = __create_nested_given_names(preceding_names)

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
