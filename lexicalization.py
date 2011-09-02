#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Arne Neumann <arne-neumann@web.de>

"""
This module shall convert C{TextPlan}s into HLDS XML structures which can 
be utilized by the OpenCCG surface realizer to produce natural language text.

TODO: move OPENCCG_BIN_PATH and GRAMMAR_PATH to a config.yml file and make them
absolute

DEBUG NOTE: 
used book table columns: [u'title', u'year', u'authors', u'keywords', 
u'lang', u'plang', u'pages', u'target', u'exercises', u'examples']
"""

import os
import re
from tempfile import NamedTemporaryFile
from commands import getstatusoutput
from nltk.featstruct import Feature
from textplan import ConstituentSet, Message
from hlds import Diamond, Sentence, create_hlds_testbed, diamond2sentence
from util import ensure_unicode, write_to_file, sql_array_to_set #TODO: dbg, rm
from database import get_column #TODO: dbg, rm

OPENCCG_BIN_PATH = "/home/guido/bin/openccg/bin"
GRAMMAR_PATH = "openccg-jpolibox"

def test_keywords():
    """
    retrieves all keywords from the database and realizes them with 
    I{ccg-realize}.
    """
    keyword_arrays = get_column("keywords")
    keyword_set = set()
    for keyword_array in keyword_arrays:
        temp_set = sql_array_to_set(keyword_array)
        for keyword in temp_set:
            keyword_set.add(keyword)
            
    keyword_diamonds = [__gen_keyword(keyword) for keyword in keyword_set]
    for diamond in keyword_diamonds:
        print realize(diamond, results="all"), "\n\n"


def realize(sentence, results="all"):
    """
    realizes a sentence by calling OpenCCG's I{ccg-realize} binary.
    
    TODO: check if 'Best Joined Edges' do play a significant role (they're not
    always present)
    
    @type sentence: C{str} or C{Diamond} or C{Sentence}
    @param sentence:
     - a string: the path to an HLDS XML sentence file (absolute path or 
       relative to GRAMMAR_PATH)
     - a Diamond instance
     - a Sentence instance
    
    @type results: C{str}
    @param results: 
    - "debug": return the raw results from ccg-realize
    - "all": return all strings that ccg-realize could produce ("Complete 
      Edges")
    - "best": return only the best result from ccg-realize ("Best Edge")
    
    @rtype: C{str} or C{list} of C{str}
    @return: a string (the "best" result from OpenCCG) OR a list of string, 
    containing "all" results that could be realized by OpenCCG
    """
    current_dir = os.getcwd()
    os.chdir(GRAMMAR_PATH)
    grammar_abspath = os.getcwd()
    realizer = os.path.join(OPENCCG_BIN_PATH, "ccg-realize")
    
    if type(sentence) is str: # realize a file
        file_path = os.path.join(grammar_abspath, sentence)
        if os.path.isfile(file_path):
            status, output = getstatusoutput("{0} {1}".format(realizer, 
                                                              file_path))
            with open(file_path, "r") as f:
                sent_xml_str = f.read() # used for results="debug"
                
            os.chdir(current_dir)
        else:
            os.chdir(current_dir)
            raise Exception, "{0} is not a file.\n" \
                "Please use an absolute path or one that is relative to:\n" \
                "{1}".format(file_path, grammar_abspath)
    
    elif type(sentence) is Diamond or type(sentence) is Sentence:
        if type(sentence) is Diamond:
            sentence = diamond2sentence(sentence)
        
        sent_xml_str = create_hlds_testbed(sentence, mode="realize", 
                                           output="xml")

        tmp_file = NamedTemporaryFile(mode="w", delete=False)
        tmp_file.write(sent_xml_str)
        tmp_file.close()

        status, output = getstatusoutput("{0} {1}".format(realizer, 
                                                          tmp_file.name))
        os.chdir(current_dir)
        
    else:
        os.chdir(current_dir)
        raise Exception, "Sorry, I can only realize HLDS XML sentence files," \
            " Sentence and Diamond instances."

    if status != 0:
        raise Exception, "Error: Can't run ccg-realize properly." \
            "Error message is:\n\n{0}".format(output)
    else:
        if results == "debug":
            input_and_output = \
                "Input:\n{0}\n\n\nOutput:\n{1}".format(sent_xml_str, output)
            return input_and_output

        res = re.compile("Complete Edges \(sorted\):\n")
        complete_vs_best = re.compile("\nBest Edge:\n")
        sentence_header = re.compile("\{.*?\} \[.*?\] ")
        sentence_tail = re.compile(" :- ")
        
        _, results_str = res.split(output)
        complete_edges_str, best_edge = complete_vs_best.split(results_str)

        if not complete_edges_str: #if there are no complete edges
            best_vs_best_joined = re.compile("\nBest Joined Edge:\n")
            best_edge, best_joined = best_vs_best_joined.split(best_edge)

        if results == "best":
            _, best_edge_and_tail = sentence_header.split(best_edge)
            best_result, _ = sentence_tail.split(best_edge_and_tail)
            return best_result

        elif results == "all":
            if complete_edges_str:
                complete_edges_list = complete_edges_str.splitlines()
                result_edges = []
                for complete_edge in complete_edges_list:
                    # maxsplit=1 is needed if there are 'Best Joined Edges'
                    _, edge_and_tail = sentence_header.split(complete_edge, 
                                                             maxsplit=1)
                    edge, _ = sentence_tail.split(edge_and_tail, maxsplit=1)
                    result_edges.append(edge)
                return list(set(result_edges)) # remove duplicates, return a list
            else: # if there are no complete edges
                _, best_edge_and_tail = sentence_header.split(best_edge)
                best_edge_result, _ = sentence_tail.split(best_edge_and_tail)
                _, best_joined_and_tail = sentence_header.split(best_joined)
                best_joined_result, _ = sentence_tail.split(best_joined_and_tail)
                return [best_edge_result, best_joined_result]

                
def linearize_textplan(textplan): #TODO: add better explanation to docstring
    """
    takes a text plan (RST tree) and returns an ordered list of constituent 
    sets (RST relations that combine two messages).
    
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
    for i, fs in enumerate(rest):
        if type(fs[Feature("satellite")]) is Message:
            structure = ConstituentSet(relType=fs[Feature("relType")], 
                                       satellite=fs[Feature("satellite")])
            linearized_structures.append(structure)

        elif type(fs[Feature("satellite")]) is ConstituentSet:
        # if the satellite is nested further    
            structure = ConstituentSet(relType=fs[Feature("relType")])
            linearized_structures.append(structure)

            nested_structure = fs[Feature("satellite")]
            linearized_structures.append(nested_structure)
    return linearized_structures
                 
def __rstree2list(featstruct):
    rst_list = [fs for fs in featstruct.walk() if type(fs) is ConstituentSet]
    rst_list.reverse()
    return rst_list


def lexicalize_title(book_title):
    return [gen_title(book_title), gen_abstract_title(1)]
    
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
    
    opening_bracket = Diamond()
    opening_bracket.create_diamond('99', u'a1:anf\xfchrung\xf6ffnen', 
                                   u'anf\xf6ffn', [])
    closing_bracket = Diamond()
    closing_bracket.create_diamond('66', u'a2:anf\xfchrungschlie\xdfen', 
                                   'anfschl', [])
    
    title_diamond = Diamond()
    title_diamond.create_diamond('AGENS', 'buchtitel', book_title, 
                                 [opening_bracket, closing_bracket])
    return title_diamond


def gen_abstract_title(number_of_books):
    """
    given an integer representing a number of books returns a Diamond, which 
    can be realized as either "das Buch" or "die Bücher"
    
    @type number_of_books: C{int}
    @rtype: C{Diamond}
    """
    if number_of_books is 1:
        num_str = "sing"
    if number_of_books > 1:
        num_str = "plur"

    art = Diamond()
    art.create_diamond("ART", "sem-obj", "def", [])    

    num = Diamond()
    num.create_diamond("NUM", "", num_str, [])

    title = Diamond()
    title.create_diamond("", "artefaktum", "Buch", [art, num])
    return title
    
def lexicalize_author(name):
    """
    converts the name of an author into several possible HLDS diamond 
    structures, which can be used for text generation.
    
    @type name: C{str}
    @param name: name of an author, e.g. "Christopher D. Manning"
    
    @rtype: C{list} of C{Diamond}s
    @return: a list of 3 Diamond instance. the first generates "der Autor", the
    second the author's lastname and the last generates the author's complete 
    name.
    """
    return [__gen_abstract_autor(1), __gen_lastname_only(name), 
            __gen_complete_name(name)]
        

def __gen_abstract_autor(num_of_authors):
    """
    given an integer (number of authors), returns a Diamond instance which 
    generates "der Autor" or "die Autoren".
    
    @type num_of_authors: C{int}
    @param num_of_authors: the number of authors of a book
    
    @rtype: C{Diamond}
    """
    if num_of_authors == 1:
        num_str = "sing"
    elif num_of_authors > 1:
        num_str = "plur"
        
    art = Diamond()
    art.create_diamond("ART", "d1:sem-obj", "def", [])
    gen = Diamond()
    gen.create_diamond("GEN", "", "mask", [])
    num = Diamond()
    num.create_diamond("NUM", "", num_str, [])
    
    der_autor = Diamond()
    der_autor.create_diamond("", u"a1:bel-phys-körper", "Autor", 
                            [art, gen, num])
    return der_autor


def __gen_lastname_only(name):
    """
    given an authors name ("Christopher D. Manning"), the function returns a 
    Diamond instance which can be used to realize the author's last name.
    
    NOTE: This does not work with last names that include whitespace, e.g. 
    "du Bois" or "von Neumann".
    
    TODO: remove n1, x1 from "nom" fields
    
    @type name: C{str}
    @rtype: C{Diamond}
    """
    _, lastname_str = __split_name(name)        
    lastname_only = Diamond()
    lastname_only.create_diamond("n1", "x1:personenname", "", [])
    lastname = Diamond()
    lastname.create_diamond("", "nachname", lastname_str, [lastname_only])
    return lastname


def __gen_complete_name(name):
    """
    takes a name as a string and returns a corresponding nested HLDS diamond 
    structure.
    
    @type name: C{str}
    @rtype: C{Diamond}
    """
    given_names, lastname_str = __split_name(name)
    complete_name = Diamond()
    if given_names:
        given_names_diamond = __create_nested_given_names(given_names)
        complete_name.create_diamond("", "nachname", lastname_str, 
                                     [given_names_diamond])
    else: #if name string does not contain ' ', i.e. only last name is given
        complete_name.create_diamond("", "nachname", lastname_str, [])

    return complete_name




def lexicalize_keywords(keywords):
    """
    @type keywords: C{frozenset} of C{str}
    
    TODO: add code for "das Thema" / "die Themen"
    """
    
    return [__gen_keywords(keywords)]
    

def __gen_keywords(keywords):
    """
    takes a list of keyword (strings) and converts them into a nested 
    C{Diamond} structure
    
    @type keywords: C{list} of C{str}
    @rtype: C{Diamond}
    """
    def gen_keyword(keyword):
        """takes a keyword (string) and converts it into a C{Diamond}"""
        fixed_keyword = keyword.replace(" ", "_")
        num = Diamond()
        num.create_diamond("NUM", "", "sing", [])
        keyword_diamond = Diamond()
        keyword_diamond.create_diamond("", "sorte", fixed_keyword, [num])
        return keyword_diamond

    if len(keywords) == 1:
        return [gen_keyword(keywords[0])]
    
    elif len(keywords) > 1:
        keyword_diamonds = [gen_keyword(kw) for kw in keywords]
        return __gen_enumeration(keyword_diamonds)

    

def __gen_enumeration(diamonds_list):
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
        enumeration = Diamond()
        enumeration.create_diamond("", "konjunktion", "und", 
                                   [diamonds_list[1], diamonds_list[0]])
    if len(diamonds_list) > 2:
        enumeration = Diamond()
        nested_komma_enum = __gen_komma_enumeration(diamonds_list[1:])
        enumeration.create_diamond("", "konjunktion", "und", 
                                   [nested_komma_enum, diamonds_list[0]])
    return enumeration
    

def __gen_komma_enumeration(diamonds_list):
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
    if len(diamonds_list) is 0:
        return []
    if len(diamonds_list) is 1:
        return diamonds_list[0]
    if len(diamonds_list) is 2:
        komma_enum = Diamond()
        komma_enum.create_diamond("NP1", "konjunktion", "komma", 
                                  [diamonds_list[1], diamonds_list[0]])
    if len(diamonds_list) > 2:
        komma_enum = Diamond()
        nested_komma_enum = __gen_komma_enumeration(diamonds_list[1:])
        komma_enum.create_diamond("NP1", "konjunktion", "komma", 
                                  [nested_komma_enum, diamonds_list[0]])
    return komma_enum
    

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
        diamond = Diamond()
        nested_diamond = __create_nested_given_names(preceding_names)

        if type(nested_diamond) is list:
            diamond.create_diamond("N1", "vorname", last_given_name, 
                                   nested_diamond)
        elif type(nested_diamond) is Diamond:
            diamond.create_diamond("N1", "vorname", last_given_name, 
                                   [nested_diamond])            
        return diamond
        
    else: # given_names list is empty
        return []

