#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Arne Neumann <arne-neumann@web.de>

"""
The I{messages} module contains the C{Message} class and related classes.

C{Message}s contain propositions about books. The text planner applies
C{Rule}s to these C{Message}s to form C{ConstituentSet}s. C{Rule}s will
also be applied to C{ConstituentSet}s, ultimately forming one C{TextPlan}
that contains all the information to be realized.
"""

import nltk
from nltk import FeatDict, Feature


class Message(nltk.featstruct.FeatDict):
    """
    A {Message} combines and stores knowledge about an object (here: books) 
    in a logical structure. Messages are constructed 
    during content selection (taking the user's requirements, querying a 
    database and processing its results), which precedes text planning.

    Each C{Message} has a I{msgType} which describes the kind of information 
    it includes. For example, the msgType 'id' specifies information that is 
    needed to distinguish a book from other books::
    
        [ *msgType*    = 'id'                                ]
        [ authors      = frozenset(['Roland Hausser'])       ]
        [ codeexamples = 0                                   ]
        [ language     = 'German'                            ]
        [ pages        = 572                                 ]
        [ proglang     = frozenset([])                       ]
        [ target       = 0                                   ]
        [ title        = 'Grundlagen der Computerlinguistik' ]
        [ year         = 2000                                ]
    """
    def __init__(self, msgType = None):
        """
        I{msgType} is only specified for the C{nltk.featstruct.FeatDict} if it 
        is specified by the user.
        """
        if msgType: 
            self[nltk.featstruct.Feature('msgType')] = msgType


class Messages:
    """
    represents all C{Message} instances generated from C{Propositions} about a 
    C{Book}.
    """
    def __init__ (self, propositions):
        """reads propositions and calls message generation functions 
        
        @type propositions: C{Propositions}
        @param propositions: a C{Propositions} class instance
        """
        self.book_score = propositions.book_score
        self.propositions = propositions.propositions
        self.messages = {}

        # does not generate a message if there are no propositions about 
        # its content (e.g. about 'extra')
        for proposition_type in self.propositions.iterkeys():
            if self.propositions[proposition_type]:
                self.messages[proposition_type] = \
                    self.generate_message(proposition_type)

    def generate_message(self, proposition_type):
        """
        generates a C{Message} from a 'simple' C{Proposition}. Simple 
        propositions are those kinds of propostions that only give information 
        about one item (i.e. describe one book) but don't compare two items 
        (e.g. book A is 12 years older than book B).
        """
        message = Message(msgType = proposition_type)
        proposition_dict = self.propositions[proposition_type]
        simple_propositions = set(('id', 'lastbook_match', 'usermodel_match', 
                                   'usermodel_nomatch')) 
        #simple_propositions can be turned into messages without 
        #further 'calculations'
        
        
        #keywords, authors and proglangs are stored as sets, but we need 
        #frozensets (hashable) when creating rules and checking for duplicate 
        #messages
        if proposition_type in simple_propositions:
            for attrib in proposition_dict.iterkeys():
                value, rating = proposition_dict[attrib]
                if type(value) == set: 
                    value = frozenset(value)
                message.update({attrib: (value, rating)})
    
        if proposition_type is 'extra':
            message = self.generate_extra_message(proposition_dict)
    
        if proposition_type is 'lastbook_nomatch':
            message = self.generate_lastbook_nomatch_message(proposition_dict)
    
        if message[Feature("msgType")] is not 'id':
            message = self.add_identification_to_message(message)

        return message
                             
    def generate_extra_message(self, proposition_dict):
        """
        generates a C{Message} from an 'extra' C{Proposition}. Extra 
        propositions only exist if a book is remarkably new / old or very 
        short / long. 
        """
        msg = Message(msgType='extra')
        for attrib in proposition_dict.iterkeys():
            if attrib == 'year':
                description, rating = proposition_dict['year']
                recency = FeatDict({'description': description, 
                                    'rating': rating})
                msg.update({'recency': recency})
            else:
                value, rating = proposition_dict[attrib]
                if type(value) == set: 
                    value = frozenset(value)
                msg.update({attrib: (value, rating)})
        return msg 
        
    def generate_lastbook_nomatch_message(self, proposition_dict):
        """
        generates a C{Message} from a 'lastbook_nomatch' C{Proposition}. A 
        lastbook_nomatch propositions states which differences exist between 
        two books.
        """
        msg = Message(msgType='lastbook_nomatch')
        for attrib in proposition_dict.iterkeys():
            if attrib == 'longer':
                pages, rating = proposition_dict['longer']
                magnitude = FeatDict({'number': pages, 'unit': 'pages'})
                length = FeatDict({'type': 'RelativeVariation', 
                                   'direction': '+', 'magnitude': magnitude,
                                   'rating': rating})
                msg.update({'length': length})
            elif attrib == 'shorter':
                pages, rating = proposition_dict['shorter']
                magnitude = FeatDict({'number': pages, 'unit': 'pages'})
                length = FeatDict({'type': 'RelativeVariation', 
                                   'direction': '-', 'magnitude': magnitude,
                                   'rating': rating})
                msg.update({'length': length})
            elif attrib == 'newer':
                years, rating = proposition_dict['newer']
                magnitude = FeatDict({'number': years, 'unit': 'years'})
                recency = FeatDict({'type': 'RelativeVariation', 
                                    'direction': '+', 'magnitude': magnitude,
                                    'rating': rating})
                msg.update({'recency': recency})
            elif attrib == 'older':
                years, rating = proposition_dict['older']
                magnitude = FeatDict({'number': years, 'unit': 'years'})
                recency = FeatDict({'type': 'RelativeVariation', 
                                    'direction': '-', 'magnitude': magnitude,
                                    'rating': rating})
                msg.update({'recency': recency})
            else:
                value, rating = proposition_dict[attrib]
                if type(value) == set: 
                    value = frozenset(value)
                msg.update({attrib: (value, rating)})
        return msg

    def add_identification_to_message(self, message):
        """
        Adds special 'reference_title' and 'reference_authors' attributes to 
        messages other than the I{id_message}. 
        
        In contrast to the I{id_message}, other messages will not be used to 
        produce sentences that contain their content (i.e. no statement of the 
        'author X wrote book Y in 1979' generated from an 'extra_message' or a 
        'lastbook_nomatch' message). Nevertheless, they will need to make 
        reference to the title and the authors of the book (e.g. 'Y is a 
        rather short book'). As an example, look at this 'usermodel_match' 
        message::
        
            [ *msgType*           = 'usermodel_match'                     ]
            [ *reference_authors* = frozenset(['Ulrich Schmitz'])         ]
            [ *reference_title*   = 'Computerlinguistik. Eine Einführung' ]
            [ language            = 'German'                              ]
            [ proglang            = frozenset(['Lisp'])                   ]
            
        The message contains two bits of information (the language and 
        programming language used), which both have regular strings as keys. 
        The 'referential' keys on the other hand are C{nltk.Feature} 
        instances and not strings. This distinction should be regarded as 
        a syntactic trick used to emphasize a semantic differce (READ: if you 
        have a better solution, please change it).
        """
        for attrib in ('title', 'authors'):
            value, rating = self.propositions['id'][attrib]
            if type(value) == set: 
                value = (frozenset(value), rating)
            else:
                value = (value, rating)
            reference = Feature("reference_"+attrib)
            message.update({reference: value})
        return message
        
    def __str__(self):
        ret_str = ""
        ret_str += "book score: {0}\n\n".format(self.book_score)
        for message in self.messages.iterkeys():
            if self.messages[message]:
                ret_str += "{0}\n\n".format(self.messages[message])
        return ret_str

class AllMessages:
    """
    represents all Messages generated from AllPropositions about all Books()
    that were returned by a query
    """
    def __init__ (self, allpropositions):
        """
        @type allpropositions: C{AllPropositions}
        @param allpropositions: a C{AllPropositions} class instance containing 
        a list of C{Propositions} instances
        
        This will genenerate a C{Messages} instance (containing all C{Message}s
        about a book) for each C{Propositions} instance. It also adds a 
        'lastbook_title' and 'lastbook_author' to C{Message}s that compare the 
        current and the preceding book
        """
        propositions_list = allpropositions.books
        self.books = []
        lastbook_id_messages = ['lastbook_match', 'lastbook_nomatch']
        
        for index, book in enumerate(propositions_list):
            if index == 0:
                self.books.append(Messages(book))
            else:
                lastbook = propositions_list[index-1]
                for message_type in lastbook_id_messages:
                    book.propositions[message_type]['lastbook_title'] = \
                        lastbook.propositions['id']['title']
                    book.propositions[message_type]['lastbook_authors'] = \
                        lastbook.propositions['id']['authors']
                self.books.append(Messages(book))

            
    def __str__(self):
        ret_str = ""
        for index, book in enumerate(self.books):
            ret_str += "book #{0} is described with these messages:\n".format(index) + \
                       "==========================================\n\n{0}".format(book)
        return ret_str

