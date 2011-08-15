#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Arne Neumann <arne-neumann@web.de>

"""
This module shall convert C{TextPlan}s into HLDS XML structures which can 
be utilized by the OpenCCG surface realizer to produce natural language text.
"""

from nltk.featstruct import Feature
from textplan import ConstituentSet, Message
import hlds

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
    names, rating = authors
    names_list = list(names)
    
    if len(names_list) == 1:
        pass
        """
        der Autor
        die Autorin ???
        Nachname
        Vorname+ Nachname
        """
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
