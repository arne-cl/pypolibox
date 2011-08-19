#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Arne Neumann <arne-neumann@web.de>

"""
This module shall convert C{TextPlan}s into HLDS XML structures which can 
be utilized by the OpenCCG surface realizer to produce natural language text.
"""

from nltk.featstruct import Feature
from textplan import ConstituentSet, Message
from hlds import Diamond, Sentence, create_hlds_testbed
from debug import enumprint #TODO: dbg, rm

def linearize_textplan(textplan):
    """
    @type textplan: C{TextPlan}
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

def lexicalize_authors(authors):
    """
    type authors: C{tuple} of (C{frozenset}, C{str})
    """
    names, _ = authors
    names_list = list(names)
    
    if len(names_list) == 1:
        names_hlds = []
        
        # string "der Autor"
        
        art = Diamond()
        art.create_diamond("ART", "d1:sem-obj", "def", [])
        gen = Diamond()
        gen.create_diamond("GEN", "", "mask", [])
        num = Diamond()
        num.create_diamond("NUM", "", "sing", [])
        
        der_autor = Sentence()
        der_autor.create_sentence("der Autor", 1, "a1:bel-phys-körper", 
                                  "Autor", [art, gen, num])

        names_hlds.append(der_autor)
        
        # lastname
        
        _, lastname_str = __split_name(names_list[0])
        
        lastname_only = Diamond()
        lastname_only.create_diamond("n1", "x1:personenname", "", [])
        lastname = Sentence()
        lastname.create_sentence(lastname_str, 1, "nachname", lastname_str,
                                 [lastname_only])
        
        names_hlds.append(lastname)
        
        # given name(s) + lastname 
        
        return names_hlds
        
        
    elif len(names_list) > 1:
        pass
        """
        die Autoren
        
        if len(names_list) == 2:
        
        Nachname und Nachname
        Vorname+ Nachname und Vorname+ Nachname
        
        if len(names_list) > 2:

        Nachname, Nachname und Nachname
        Vorname+ Nachname, Vorname+ Nachname und Vorname+ Nachname

        #cf. database.py ...
        if len(queries) > 1:
            for query in queries[:-1]:
            #combine queries with " AND ", but don't append
            #after the last query
                combined_queries += query + query_combinator
            combined_queries += queries[-1]
            return query_template + where + combined_queries
        
        """

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
