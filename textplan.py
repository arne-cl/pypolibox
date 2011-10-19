#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Arne Neumann <arne-neumann@web.de>

# TODO: change Sequence to Joint. Sequence is a multinuclear relation which 
# combines predecessors and successors. Joint is a random relation without 
# any restrictions.

"""
The I{textplan} module is based on Nicholas FitzGerald's I{py_docplanner}[1], 
in particular on his idea to represent RST trees as attribute value matrices 
by using the I{nltk.featstruct} data structure.

I{textplan} converts C{Proposition} instances into C{Message}s (using 
attribute value notation). Via a set of C{Rule}s, these messages are combined 
into C{ConstituentSet}s. Rules are applied bottom-up, via a recursive 
best-first search (cf. I{__bottom_up_search}).

Not only messages, but also constituent sets can be combined 
via rules. If all messages present can be combined into one large 
C{ConstituentSet}, this constituent set is called a C{TextPlan}. A 
C{TextPlan} represents a complete text plan in form of an attribute value 
matrix.

[1] Fitzgerald, Nicholas (2009). Open-Source Implementation of Document 
Structuring Algorithm for NLTK. 
"""

from time import time
import nltk
from nltk.featstruct import Feature
#from nltk import FeatDict

from util import flatten, freeze_all_messages, msgs_instance_to_list_of_msgs
from rules import Rules, ConstituentSet
from messages import Message, Messages






class TextPlan(nltk.featstruct.FeatDict):
    """
    C{TextPlan} is the output of Document Planning. A TextPlan consists of an 
    optional title and text, and a child I{ConstituentSet}.
    """
    def __init__(self, book_score=None, dtype='TextPlan', text=None,
                 children=None):
        self[nltk.featstruct.Feature('type', display='prefix')] = 'TextPlan'
        self['title'] = nltk.featstruct.FeatDict({'type': dtype, 'text':text, 
                                                  'book score': book_score})
        self['children'] = children

class TextPlans:
    """
    generates all C{TextPlan}s for an C{AllMessages} instance, i.e. one 
    DocumentPlan for each book that is returned as a result of the user's 
    database query
    """
    
    def __init__ (self, allmessages):
        #generate all C{Rule}s that the C{Message}s will be checked against
        rules = Rules().rules 
        self.document_plans = []
        for index, book in enumerate(allmessages.books):
            before = time()
            
            messages = book.messages.values() # all messages about a single book
            plan = generate_textplan(messages, rules, book.book_score)
            
            after = time()
            time_diff = after - before
            self.document_plans.append(plan)
            print "Plan {0}: generated in {1} seconds.\n".format(index, time_diff, plan)
            if index > 0:
                lastbook = allmessages.books[index-1]
                print "Comparing '{0}' with '{1}':\n\n{2}".format(book.messages['id']['title'], lastbook.messages['id']['title'], plan)
            else:
                print "Describing '{0}':\n\n{1}".format(book.messages['id']['title'], plan)




def generate_textplan(messages, rules=Rules().rules, book_score = None, 
                      dtype = None, text = None):
    '''
    The main method implementing the Bottom-Up document structuring algorithm 
    from "Building Natural Language Generation Systems" figure 4.17, p. 108.

    The method takes a list of C{Message}s and a set of C{Rule}s and creates a 
    document plan by repeatedly applying the highest-scoring Rule-application 
    (according to the Rule's heuristic score) until a full tree is created. 
    This is returned as a C{TextPlan} with the tree set as I{children}.

    If no plan is reached using bottom-up, I{None} is returned.

    @param messages: a list of C{Message}s which have been selected during 
    content selection for inclusion in the TextPlan
    @type messages: list of C{Message}s
    @param rules: a list of C{Rule}s specifying relationships which can hold 
    between the messages
    @type rules: list of C{Rule}s
    @param dtype: an optional type for the document
    @type dtype: string
    @param text: an optional text string describing the document
    @type text: string
    @return: a document plan. if no plan could be created: return None
    @rtype: C{TextPlan} or C{NoneType}
    '''
    if isinstance(messages, list):
        frozen_messages = freeze_all_messages(messages)
    elif isinstance(messages, Messages):
        book_score = messages.book_score
        message_list = msgs_instance_to_list_of_msgs(messages)
        frozen_messages = freeze_all_messages(message_list)
        
    messages_set = set(frozen_messages) # remove duplicate messages    
    ret = __bottom_up_search(messages_set, rules)

    if ret: # if __bottom_up_search has found a valid plan ...
        children =  ret.pop() 
        # pop returns an 'arbitrary' set element (there's only one)
        return TextPlan(book_score=book_score, dtype=dtype, 
                        text=text, children=children)
    else:
        return None

def __bottom_up_search(messages, rules):
    '''generate_text() helper method which performs recursive best-first-search

    @param messages: a set containing C{Message}s and/or C{ConstituentSet}s
    @type messages: C{set} of C{Message}s or C{ConstituentSet}s
    
    @param rules: a list of C{Rule}s specifying relationships which can hold 
    between the messages
    @type rules: C{list} of C{Rule}s
        
    @return: a set containing one C{Message}, i.e. the first valid plan reached
    by best-first-search. returns None if no valid plan is found.
    @rtype: C{NoneType} or a C{set} of (C{Message}s or C{ConstituentSet}s)
    '''
    if len(messages) == 1:
        return messages
    elif len(messages) < 1:
        raise Exception('ERROR')
    else:
        try:
            options = [rule.get_options(messages) for rule in rules]
        except:
            raise Exception('ERROR: Rule {0} had trouble with these messages: {1}'.format(rule, messages))
            print "ERROR" #TODO: remove after debugging
            
        options = flatten(options)
        options_list = []
        for x, y, z in options:
            y.freeze()
            options_list.append( (x, y, z) )
            
        if options_list == []:
            return None

        #sort all options by their score, beginning with the highest one
        sorted_options = sorted(options_list, key = lambda (x,y,z): x, 
                                reverse=True) 
                                
        for (score, rst_relation, removes) in sorted_options:
            '''
            rst_relation: a ConstituentSet (RST relation) that was generated by
                Rule.get_options()
            removes: a list containing those messages that are now part of 
                'rst_relation' and should therefore not be used again
            '''
            testSet = messages - set(removes)
            testSet = testSet.union(set([rst_relation]))
            # a set containing a ConstituentSet and one or more Messages that 
            # haven't been integrated into a structure yet

            ret = __bottom_up_search(testSet, rules)
            if ret:
                return ret
        return None


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


