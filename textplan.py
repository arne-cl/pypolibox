#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Arne Neumann <arne-neumann@web.de>

# TODO: change Sequence to Joint (just change the name). Sequence is a
# multinuclear relation which combines predecessors and successors. Joint
# is a random relation without any restrictions.

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


import nltk
from nltk.featstruct import Feature, FeatDict
from lxml import etree
from time import time

from util import (flatten, freeze_all_messages, msgs_instance_to_list_of_msgs,
                  ensure_unicode)
from rules import Rules, ConstituentSet
from messages import Message, Messages
from hlds import etreeprint # TODO: dbg, rm


class TextPlan(nltk.featstruct.FeatDict):
    """
    C{TextPlan} is the output of Document Planning. A TextPlan consists of an 
    optional title and text, and a child I{ConstituentSet}.
    """
    def __init__(self, book_score=None, dtype='TextPlan', text=None,
                 children=None):
        self[nltk.featstruct.Feature('type', display='prefix')] = dtype
        self['title'] = nltk.featstruct.FeatDict({'text':text, 
                                                  'book score': book_score})
        self['children'] = children

class TextPlans(object):
    """
    generates all C{TextPlan}s for an C{AllMessages} instance, i.e. one 
    DocumentPlan for each book that is returned as a result of the user's 
    database query
    """
    
    def __init__ (self, allmessages, debug=False):
        #generate all C{Rule}s that the C{Message}s will be checked against
        rules = Rules().rules 
        self.document_plans = []
        for index, book in enumerate(allmessages.books):
            before = time()
            
            messages = book.messages.values() #all messages about a single book
            plan = generate_textplan(messages, rules, book.book_score)
            
            after = time()
            time_diff = after - before
            self.document_plans.append(plan)

            if debug == True:
                print "Plan {0}: generated in {1} seconds.\n".format(index,
                                                                     time_diff,
                                                                     plan)
                book_title = book.messages['id']['title']
                
                if index > 0:
                    lastbook = allmessages.books[index-1]
                    lastbook_title = lastbook.messages['id']['title']
                    print "Comparing '{0}' " \
                          "with '{1}':\n\n{2}".format(book_title,
                                                      lastbook_title, plan)
                else:
                    print "Describing '{0}':\n\n{1}".format(book_title, plan)




def generate_textplan(messages, rules=Rules().rules, book_score = None, 
                      dtype = 'TextPlan', text = ''):
    """
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
    """
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
    """generate_text() helper method which performs recursive best-first-search

    @param messages: a set containing C{Message}s and/or C{ConstituentSet}s
    @type messages: C{set} of C{Message}s or C{ConstituentSet}s
    
    @param rules: a list of C{Rule}s specifying relationships which can hold 
    between the messages
    @type rules: C{list} of C{Rule}s
        
    @return: a set containing one C{Message}, i.e. the first valid plan reached
    by best-first-search. returns None if no valid plan is found.
    @rtype: C{NoneType} or a C{set} of (C{Message}s or C{ConstituentSet}s)
    """
    if len(messages) == 1:
        return messages
    elif len(messages) < 1:
        raise Exception('ERROR')
    else:
        try:
            options = [rule.get_options(messages) for rule in rules]
        except:
            raise Exception('ERROR: Rule {0} had trouble with these ' \
                            'messages: {1}'.format(rule, messages))
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
            """
            rst_relation: a ConstituentSet (RST relation) that was generated by
                Rule.get_options()
            removes: a list containing those messages that are now part of 
                'rst_relation' and should therefore not be used again
            """
            testSet = messages - set(removes)
            testSet = testSet.union(set([rst_relation]))
            # a set containing a ConstituentSet and one or more Messages that 
            # haven't been integrated into a structure yet

            ret = __bottom_up_search(testSet, rules)
            if ret:
                return ret
        return None


def linearize_textplan(textplan):
    """
    takes a text plan (an RST tree represented as a NLTK.featstruct data
    structure) and returns an ordered list of C{Message}s for surface
    generation.

    @type textplan: C{TextPlan}
    @rtype: C{list} of C{Message}s
    """
    return [elem for elem in textplan.walk() if type(elem) is Message]


def textplans2xml(textplans):
    """
    converts several C{TextPlan}s into an XML structure representing
    these text plans.
    
    @type textplans: a C{TextPlans} instance
    @rtype: C{etree._ElementTree}
    """
    root = etree.Element("xml")
    for textplan in textplans.document_plans:
        xml_textplan = __textplan_header2xml(root, textplan)
        # text plans are inserted into the ElementTree
    
    doc = etree.ElementTree(root)
    return doc
    

def textplan2xml(textplan):
    """
    converts one C{TextPlan} into an XML structure representing it.
    
    @type textplans: C{TextPlan}
    @rtype: C{etree._ElementTree}
    """
    root = etree.Element("xml")
    xml_textplan = __textplan_header2xml(root, textplan) # text plan inserted
                                                         # into the ElementTree
    doc = etree.ElementTree(root)
    return doc

def __textplan_header2xml(tree_root, textplan):
    
    xml_textplan = etree.SubElement(tree_root, "textplan")

    book_score = str(textplan["title"]["book score"])
    document_type = textplan[Feature("type")]
    target_string = textplan["title"]["text"]

    header = etree.SubElement(xml_textplan, "header", score=book_score,
                              type=document_type)
    target = etree.SubElement(header, "target")
    target.text = target_string

    rst_tree = __textplantree2xml(textplan["children"])
    xml_textplan.insert(1, rst_tree)
    return xml_textplan


def __textplantree2xml(tree):
    if isinstance(tree, ConstituentSet):
        relation_type = tree[Feature("relType")]
        nucleus_tree = __textplantree2xml(tree[Feature("nucleus")])
        satellite_tree = __textplantree2xml(tree[Feature("satellite")])

        relation = etree.Element("relation", type=relation_type)
        nucleus = etree.SubElement(relation, "nucleus")
        nucleus.insert(0, nucleus_tree)
        satellite = etree.SubElement(relation, "satellite")
        satellite.insert(0, satellite_tree)
        return relation
        
    elif isinstance(tree, Message):
        return __message2xml(tree)


def __message2xml(message):        
    msg_type = message[Feature("msgType")]
    msg = etree.Element("message", type=msg_type)

    msg_elements = [(key, val) for (key, val) in message.items()
                               if key != Feature("msgType")]
    for key, val in msg_elements:
        if isinstance(key, str):
            if isinstance(val, FeatDict): #relative length or recency
                rating = val["rating"]
                if "type" in val:
                    val_type = val["type"]
                    direction = val["direction"]
                    number = str(val["magnitude"]["number"])
                    unit = val["magnitude"]["unit"]
                    msgkey = etree.SubElement(msg, key, rating=rating,
                                              type=val_type)
                    msgval = etree.SubElement(msgkey, "magnitude",
                                              number=number, unit=unit,
                                              direction=direction)
                else: # "extra" recency or length
                    description = val["description"]
                    msgkey = etree.SubElement(msg, key, description=description,
                                              rating=rating, type="extra")
                    
                    

            elif isinstance(val, tuple): # (value, rating) tuple
                value, rating = val
                if isinstance(value, frozenset):
                    msgkey = etree.SubElement(msg, key, rating=rating)
                    for element in value:
                        msgval = etree.SubElement(msgkey, "value")
                        msgval.text = ensure_unicode(element)
                else:
                    msgkey = etree.SubElement(msg, key,
                                              value=ensure_unicode(value),
                                              rating=rating)
                                              
        else: #if isinstance(key, Feature):
            value, rating = val
            if isinstance(value, frozenset):
                featkey = etree.SubElement(msg, key.name, feature="true",
                                           rating=rating)
                for element in value:
                    featval = etree.SubElement(featkey, "value")
                    featval.text = str(element)
            else:
                featkey = etree.SubElement(msg, key.name, feature="true",
                                           value=ensure_unicode(value),
                                           rating=rating)
    return msg


def test():
    import cPickle
    atp = cPickle.load(open("data/alltextplans.pickle", "r"))
    #return atp
    print """### One file per query ###\n\n"""
    for atp_count, textplans in enumerate(atp):
            xml_plan = textplans2xml(textplans)
            print atp_count, "+++++\n"
            print etreeprint(xml_plan, debug=False), "\n\n\n"

    print """### One file per text plan ###\n\n"""
    for atp_count, tp in enumerate(atp):
        for tp_count, docplan in enumerate(tp.document_plans):
            xml_plan = textplan2xml(docplan)
            print atp_count, tp_count, "+++++\n"
            print etreeprint(xml_plan, debug=False), "\n\n\n"

"""
import cPickle; atp = cPickle.load(open("data/alltextplans.pickle", "r")); a3d2 = atp[3].document_plans[2]
c = a3d2["children"]; idmsg = c[Feature("nucleus")][Feature("nucleus")][Feature("nucleus")][Feature("nucleus")]
from hlds import etreeprint; d = __textplantree2xml(c); etreeprint(d)
"""
