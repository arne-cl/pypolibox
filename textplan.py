#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

import itertools
from time import time
import nltk
from nltk.featstruct import Feature
from nltk import FeatDict

from util import (exists, flatten, freeze_all_messages, 
                  messages_instance_to_list_of_message_instances)


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
            self[nltk.featstruct.Feature('msgType', display='prefix')] = msgType


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
        propositions are those kind of propostions that only give information 
        about one item (i.e. describe one book) but don't compare two items 
        (e.g. book A is 12 years older than book B).
        """
        message = Message(msgType = proposition_type)
        proposition_dict = self.propositions[proposition_type]
        simple_propositions = set(('id','lastbook_match', 'usermodel_match', 
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
                value = frozenset(value)
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


class ConstituentSet(nltk.featstruct.FeatDict):
    """
    C{ConstituentSet} is the contstuction built up by applying C{Rules} to a 
    set of C{ConstituentSet}s and C{Message}s. Each C{ConstituentSet} is of a 
    specific I{relType}, and has two constituents, one which is designated the 
    I{nucleus} and one which is designated I{aux}. These C{ConstituentSet}s can
    then be combined with other C{ConstituentSet}s or C{Message}s.

    C{ConstituentSet} is based on C{nltk.featstruct.FeatDict}.
    """
    def __init__(self, relType = None, nucleus = None, satellite = None):
        """
        I{relType}, I{nucleus} and I{aux} are only specified for the 
        C{nltk.featstruct.FeatDict} if they are specified by the user.

        @param relType: The relation type which related the I{nucleus} to 
        I{aux}. 
        @type relType: string
        @param nucleus: Nucleus constituent. C{Message} or C{ConstituentSet}.
        @type nucleus: Message or ConstituentSet
        @param satellite: Auxiliary constituent. C{Message} or 
        C{ConstituentSet}. 
        @type satellite: Message or ConstituentSet
        """
        if relType: 
            self[nltk.featstruct.Feature('relType',display='prefix')] = relType
        if nucleus: 
            self[nltk.featstruct.Feature('nucleus',display='prefix')] = nucleus
        if satellite: 
            self[nltk.featstruct.Feature('satellite',display='prefix')] = satellite


class TextPlan(nltk.featstruct.FeatDict):
    """
    C{TextPlan} is the output of Document Planning. A TextPlan consists of an 
    optional title and text, and a child I{ConstituentSet}.
    """
    def __init__(self, book_score=None, dtype='TextPlan', text=None,
                 children=None):
        self[nltk.featstruct.Feature('type',display='prefix')] = 'DPDocument'
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


class Rule(object):
    '''
    C{Rules} are the elements which specify relationships which hold between 
    elements of the document. These elements can be I{Message}s or 
    I{ConstituentSet}s.

    Each I{Rule} specifies a list of I{inputs}, which are is a minimal 
    specification of a C{Message} or C{ConstituentSet}. To be a valid input to 
    this Rule, a given C{Message} or C{ConstituentSet} must subsume one of the 
    specified I{input}s.

    Each I{Rule} can also specify a set of conditions which must be met in 
    order for the Rule to hold between the inputs.

    Each I{Rule} specifies a heuristic, which will be evaluated to provide a 
    score by which to rank the order in which rules should be applied.

    Each I{Rule} specifies which of the inputs will be the I{nucleus} and which
    will be the I{aux} of the output C{ConstituentSet}.
    '''

    def __init__(self, name, ruleType, nucleus, satellite, conditions, heuristic):
        '''
        @param name: The name of the rule.
        @type name: string
        
        @param ruleType: The name of the relationship type this Rule specifies.
        @type ruleTupe: string
            
        @param conditions: a list of strings which will be evaluated as 
        conditions for applying the rule. These should return True or False 
        when evaluated
        @type conditions: list of strings
      
        @param nucleus: A list of tuples containing (name, input). I{name} is 
        a string specifying the name used for the nucleus message of the RST 
        relation. The name is used to refer to this message in the 
        I{conditions} and I{heuristic}. I{input} is a C{Message} or 
        C{ConstituentSet}. There can be only one nucleus in a RST relation, so 
        the planner has to choose from the list. 
        @type nucleus: list of tuples: (string, C{Message} or 
        C{ConstituentSet}) 
      
        @param satellite: same as I{nucleus}, but represents a list of possible
        satellite messages of a RST relation. Again, there can be only one 
        satellite in a RST relation, so the planner has to choose from the 
        list. 
        
        @param heuristic: an integer used to rank potential ConstituentSets. 
        @type heuristic: C{int}
        '''
        self.name = name
        self.ruleType = ruleType
        self.conditions = conditions
        self.nucleus = nucleus
        self.satellite = satellite
        self.heuristic = heuristic

    def __str__(self):
        """
        string output for debugging purposes.
        """
        ret = ''
        for (key, val) in self.__dict__.iteritems():
            ret += str(key) + ' - ' + str(val) + '\n'
        return ret

    def get_options(self, messages):
        """these main method used for document planning 
        
        From the list of C{Messages}, I{get_options} selects all possible ways 
        the Rule could be applied.

        The planner can then select -- with the __bottom_up_search function -- 
        one of these possible applications of the Rule to use.
        
        I{non_empty_message_combinations} is a list of combinations, where each
        combination is a (nucleus, satellite)-tuple. both the nucleus and the 
        satellite each consist of a (name, message) tuple.

        @type messages: list of C{Message} objects
        @param messages: a list of C{Message} objects, each containing one 
        message about a book
        
        @rtype: empty list or a list containing one C{tuple} of (C{int}, 
        C{ConstituentSet}, C{list}), where C{list} consists of C{Message} 
        or C{ConstituentSet} objects 
        @return: a list containing one 3-tuple 
        (score, C{ConstituentSet}, inputs}) where:
            score is the evaluated heuristic score for this application 
                of the Rule
            const_set is the new C{ConstituentSet} returned by the application 
                of the Rule
            inputs is the list of inputs (C{Message}s or C{ConstituentSets} 
                used in this application of the rule
        The method returns an empty list if I{get_options} can't find a way 
        to apply the I{Rule}.
        """
        self.messages = messages # will be used by self.__name_eval()
        nucleus_candidates = []
        satellite_candidates = []

        for message_prototype in self.nucleus:
            nucleus_candidates.extend( self.find_message_candidates(messages, message_prototype) )

        for message_prototype in self.satellite:
            satellite_candidates.extend( self.find_message_candidates(messages, message_prototype) )
        
        possible_msg_combinations = list(itertools.product(nucleus_candidates, satellite_candidates)) #cartesian product (all possible combinations) of nucleus and satellite messages 
        
        condition_matching_combinations = self.get_satisfactory_groups(possible_msg_combinations) #remove messages which do not satisfy conditions
        
        non_empty_message_combinations = [msgs for msgs in condition_matching_combinations if msgs != [] ] # remove empty messages

        self.combinations = non_empty_message_combinations #TODO: remove after debugging
        
        #return nucleus_candidates, satellite_candidates, possible_msg_combinations, condition_matching_combinations, non_empty_message_combinations #TODO: remove
 
        options_list = []
        inputs = []
        for i, combination in enumerate(non_empty_message_combinations):
            score = self.heuristic
            constituent_set = self.__get_return(combination)
            (nucleus_name, nucleus_msg), (sat_name, sat_msg) = combination
            inputs.append(nucleus_msg)
            inputs.append(sat_msg)
            options_list.append( (score, constituent_set, inputs) )
        return options_list            

    def find_message_candidates(self, messages, message_prototype):
        """takes a list of messages and returns only those with the right 
        message type (as specified in Rule.inputs)
        
        @type messages: C{list} of C{Message}s
        @param messages: a list of C{Message} objects, each containing one 
        message about a book

        @param message_prototype: a tuple consisting of a message name and a 
        C{Message} or C{ConstituentSet}
        @type message_prototype: C{tuple} of (string, C{Message} or 
        C{ConstituentSet})

        @rtype: C{list} of C{tuple}s of (string, C{Message})
        @return: a list containing all (name, message) tuples which are 
        subsumed by the input message type (self.nucleus or self.satellite). 
        If a rule should only be applied to UserModelMatch and UserModelNoMatch
        messages, the return value contains a list of messages with these 
        types. 
        """
        messages_list = []
        name, condition = message_prototype
        for message in messages:            
            if condition.subsumes(message):
                messages_list.append( (name, message) )
        return messages_list
        
    def get_satisfactory_groups(self, groups):    
        '''
        @type groups: C{list} of C{list}'s of C{tuple}'s of (C{str}, 
        C{Message} or C{ConstituentSet})
        @param groups: a list of group elements. each group contains a list 
        which contains one or more message tuples of the form 
        (message name, message)
        
        @rtype: C{list} of C{list}'s of C{tuple}'s of (C{str}, C{Message} 
        or C{ConstituentSet})
        @return: a list of group elements. contains only those groups which 
        meet all the conditions specified in self.conditions        
        '''
        satisfactory_groups = []
        for group in groups:
            if all(self.get_conditions(group)) is True:
                satisfactory_groups.append(group)
        return satisfactory_groups
        
    def get_conditions(self, group):
        '''applies __name_eval to all conditions a Rule has, i.e. checks if a 
        group meets all conditions
        
        @type group: C{list} of C{tuple}'s of (C{str}, C{Message} or 
        C{ConstituentSet})
        @param group: a list of message tuples of the form 
        (message name, message)

        @rtype: C{list} of C{bool}
        @return: a list of truth values, each of which tells if a group met 
        all conditions specified in self.conditions
        '''
        results = []
        for condition in self.conditions:
            try:
                results.append( self.__name_eval(condition, group) )
            except NameError:
                # __name_eval can check for the existence of an object, but it
                # will fail to "do something" with a nonexisting object, e.g. 
                # "len(lastbook_match) < 5" would raise an error if 
                # lastbook_match doesn't exist
                results.append(False)
        return results
                
    def __name_eval(self, condition, group):
        '''Evaluate if I{condition} is met by the C{message}s in I{group}
        
        @type condition: C{str}
        @param condition: a python statement that can be evaluated to True or 
        False, encoded as a string
        
        @type group: C{list} of C{tuple}'s of (C{str}, C{Message} or 
        C{ConstituentSet})
        @param group: a list of message tuples of the form 
        (message name, message)
        
        C{Message}s and C{ConstituentSet}s are C{FeatDict}s, which can be 
        queried just like normal C{dict}s.
        
        @rtype: C{bool}
        @return: True if the condition is met by the C{Message}s in I{group}
        '''
        for message in self.messages:
            if Feature("msgType") in message: 
            #if it's a C{Message} and not a C{ConstituentSet}
                message_name = message[Feature("msgType")]
                locals()[message_name] = message

        try:
            ret = eval(condition)
        except AttributeError:
            ret = False
        return ret

    def __get_return(self, combination):
        '''constructs a ConstituentSet returned by I{get_options}

        @type combination: C{tuple} of two C{tuple}s of (C{str}, C{Message} 
        or C{ConstituentSet})
        @param combination: a tuple of two message tuples -- the first one 
        represents the nucleus, the second one the satellite -- of the form 
        (message name, message) that will be combined into a constituent set.

        @rtype: C{ConstituentSet}
        @return: a C{ConstituentSet}, which combines a nucleus and satellite. 
        both can either be a C{Message} or C{ConstituentSet}
        '''
        (nucleus_name, nucleus_msg), (sat_name, sat_msg) = combination
        return ConstituentSet(relType = self.ruleType, nucleus=nucleus_msg, 
                              satellite=sat_msg)

class Rules():
    """creates Rule() instances
    
    Each rule of the form Rule(ruleType, inputs, conditions, nucleus, aux, 
    heuristic) is generated by its own method. Important note: these methods 
    have to adhere to a naming convention, i.e. begin with 'genrule_'; 
    otherwise, self.__init__ will fail! 
    """
        
    def __init__ (self):
        """calls methods to generate rules and saves these in self.rules"""
        self.rules = []
        self.rule_dict = {} #not necessary, but handy. cf. findrules()
        methods_list = dir(self) #lists all methods of Rules()
        for method_name in methods_list:
            if method_name.startswith('genrule_'):
                method = 'self.' + method_name + '()'
                rule = eval(method) # calls a method that generates a rule
                self.rules.append(rule)
                self.rule_dict[rule.name] = rule
                
    def __str__(self):
        ret_str = ""
        for name, rule in self.rule_dict.iteritems():
            rule_summary = "{0}({1}, {2})".format(rule.ruleType, rule.nucleus,
                                                  rule.satellite)
            ret_str += "{0}: {1}\n\n".format(name, rule_summary)
            ret_str += "{0}\n\n".format(str(rule))
        return ret_str


    def genrule_id_extra_sequence(self):
        '''Sequence(id_complete, extra), if 'extra' exists:
        
        adds an additional "sentence" about extra facts after the id messages'''
        nucleus = [('id', Message('id'))]
        satellite = [('extra', Message('extra'))]
        conditions = ['exists("extra", locals())']
        return Rule('id_extra_sequence', 'Sequence', nucleus, satellite, 
                    conditions, 10)
    
    def genrule_id_usermodelmatch(self):
        '''Elaboration({id, id_extra_sequence}, usermodel_match), if there's no
        usermodel_nomatch
        
        Meaning: This book fulfills ALL your requirments. It was written in ...,
        contains these features ... and ... etc'''
        nucleus = [('id', Message('id')), 
                  ('id_extra_sequence', ConstituentSet(nucleus=Message('id')))] 
        satellite = [('usermodel_match', Message('usermodel_match'))]
        conditions = ['exists("usermodel_nomatch", locals()) is False']    
        return Rule('id_usermodelmatch', 'Elaboration', nucleus, satellite, 
                    conditions, 5)

    def genrule_pos_eval(self):
        '''Concession(usermodel_match, usermodel_nomatch)
        
        Meaning: Book matches many (>= 50%) of the requirements, but not all of
        them'''
        nucleus = [('usermodel_match', Message('usermodel_match'))]
        satellite = [('usermodel_nomatch', Message('usermodel_nomatch'))]
        conditions = ['len(usermodel_match) >= len(usermodel_nomatch)'] 
        return Rule('pos_eval','Concession', nucleus, satellite, conditions, 8)

    def genrule_neg_eval(self):
        '''Concession(usermodel_nomatch, usermodel_match)
        
        Meaning: Although this book fulfills some of your requirements, it 
        doesn't match most of them. Therefore, this book might not be the best 
        choice.'''
        nucleus = [('usermodel_nomatch', Message('usermodel_nomatch'))]
        satellite = [('usermodel_match', Message('usermodel_match'))]
        conditions = ['len(usermodel_match) < len(usermodel_nomatch)']
        return Rule('neg_eval','Concession', nucleus, satellite, conditions, 8)

    def genrule_single_book_complete(self):
        '''Sequence({id, id_extra_sequence}, {pos_eval, neg_eval})
        
        Meaning: The nucleus mentions all the (remaining) facts (that aren't 
        mentioned in the evaluation), while the satellite evaluates the book 
        (in terms of usermodel matches)
        '''
        nucleus = [('id', Message('id')), 
             ('id_extra_sequence', ConstituentSet(satellite=Message('extra')))]
        satellite = [('pos_eval', 
                     ConstituentSet(satellite=Message('usermodel_nomatch'))), 
                     ('neg_eval', 
                     ConstituentSet(nucleus=Message('usermodel_nomatch')))]
        conditions = []
        return Rule('single_book_complete', 'Sequence', nucleus, satellite, 
                    conditions, 3)

    def genrule_single_book_complete_usermodelmatch(self):
        '''Sequence({id, id_extra_sequence}, usermodel_match)
        
        Meaning: The satellite states that the book matches ALL the user's 
        requirements. The nucleus mentions the remaining facts about the book.
        Condition: there's no preceding book and there are only usermodel 
        matches.
        '''
        nucleus = [('id', Message('id')), 
             ('id_extra_sequence', ConstituentSet(satellite=Message('extra')))]
        satellite = [('usermodel_match', Message('usermodel_match'))]
        conditions = ['exists("usermodel_nomatch", locals()) is False', 
                      'exists("lastbook_match", locals()) is False', 
                      'exists("lastbook_nomatch", locals()) is False']
        return Rule('single_book_complete_usermodelmatch','Sequence', nucleus,
                    satellite, conditions, 4)

    def genrule_single_book_complete_usermodelnomatch(self):
        '''Sequence({id, id_extra_sequence}, usermodel_nomatch)
        
        Meaning: The satellite states that the book matches NONE of the user's 
        requirements. The nucleus mentions the remaining facts about the book.
        Condition: there's no preceding book and there are no usermodel 
        matches.
        '''
        nucleus = [('id', Message('id')), 
             ('id_extra_sequence', ConstituentSet(satellite=Message('extra')))]
        satellite = [('usermodel_nomatch', Message('usermodel_nomatch'))]
        conditions = ['exists("usermodel_match", locals()) is False', 
                      'exists("lastbook_match", locals()) is False', 
                      'exists("lastbook_nomatch", locals()) is False']
        return Rule('single_book_complete_usermodelnomatch', 'Sequence', 
                    nucleus, satellite, conditions, 2)

    def genrule_book_differences(self):
        '''Contrast({id, id_extra_sequence}, lastbook_nomatch)
        
        Meaning: id/id_extra_sequence. In contrast to book X, this book is in 
        German, targets advanced users and ...
        Condition: There are differences between the two books
        '''
        nucleus = [('id', Message('id')), 
            ('id_extra_sequence', ConstituentSet(satellite=Message('extra')))]
        satellite = [('lastbook_nomatch', Message('lastbook_nomatch'))]
        conditions = ['exists("lastbook_nomatch", locals()) is True']
        return Rule('book_differences','Contrast', nucleus, satellite, 
                    conditions, 5)

    def genrule_concession_books(self):
        '''Concession(book_differences, lastbook_match)
        
        Meaning: After 'book_differences' explains the differences between both
        books, their common features are explained.
        '''
        nucleus = [('book_differences', 
                   ConstituentSet(satellite=Message('lastbook_nomatch')))]
        satellite = [('lastbook_match', Message('lastbook_match'))]
        conditions = ['exists("lastbook_match", locals()) is True']
        return Rule('concession_books','Concession', nucleus, satellite, 
                    conditions, 5)

    def genrule_concession_book_differences_usermodelmatch(self):
        '''Concession(book_differences, usermodel_match)
        
        Meaning: 'book_differences' explains the differences between both books.
        Nevertheless, this book meets ALL your requirements ...
        Condition: All user requirements are met.
        '''
        nucleus = [('book_differences', 
                    ConstituentSet(satellite=Message('lastbook_nomatch')))]
        satellite = [('usermodel_match', Message('usermodel_match'))]
        conditions = ['exists("usermodel_nomatch", locals()) is False']
        return Rule('concession_book_differences_usermodelmatch','Concession',
                    nucleus, satellite, conditions, 5)

    def genrule_book_similarities(self):
        '''Elaboration(id_usermodelmatch, lastbook_match)
        
        Meaning: 'id_usermodelmatch' mentions that the books matches ALL 
        requirements. In addition, the book shares many features with its 
        predecessor.
        Condition: There are both differences and commonalities (>=50%) between
        the two books.
        '''
        nucleus = [('id_usermodelmatch', 
                    ConstituentSet(satellite=Message('usermodel_match')))]
        satellite = [('lastbook_match', Message('lastbook_match'))] 
        conditions = ['exists("lastbook_match", locals()) is True', 
                      'exists("lastbook_nomatch", locals()) is True', 
                      'len(lastbook_match) >= len(lastbook_nomatch)']
        return Rule('book_similarities','Elaboration', nucleus, satellite, 
                    conditions, 5)

    def genrule_no_similarities_concession(self):
        #TODO: What's the connection between this rule and 'usermodel_(no)match'?
        '''Concession({id, id_extra_sequence}, lastbook_nomatch)
        
        Meaning: Book X has these features BUT share none of them with its 
        predecessor.
        Condition: There is a predecessor to this book, but they don't share 
        ANY features.
        '''
        nucleus = [('id', Message('id')), 
                   ('id_extra_sequence', ConstituentSet(satellite=Message('extra')))]
        satellite = [('lastbook_nomatch', Message('lastbook_nomatch'))]
        conditions = ['exists("lastbook_nomatch", locals()) is True', 
                      'exists("lastbook_match", locals()) is False']
        return Rule('no_similarities_concession','Concession', nucleus, 
                    satellite, conditions, 5)


    def genrule_contrast_books_posneg_eval(self):
        #TODO: new-rules.rst rule 14 mentions that this one is only about 
        #books which share no features. WHY? 
        '''Sequence(book_differences, {pos_eval, neg_eval})
        
        Meaning: book_differences mentions the differences between the books, 
        pos_eval/neg_eval explains how many user requirements they meet 
        Conditions: matches some of the requirements
        '''
        nucleus = [('book_differences', 
                   ConstituentSet(satellite=Message('lastbook_nomatch')))]
        satellite = [('pos_eval', ConstituentSet(satellite=Message('usermodel_nomatch'))), 
                     ('neg_eval', ConstituentSet(nucleus=Message('usermodel_nomatch')))]
        conditions = ['exists("usermodel_match", locals()) is True',
                      'exists("usermodel_nomatch", locals()) is True'] 
                      #'exists("lastbook_match", locals()) is False'
        return Rule('contrast_books_posneg_eval','Sequence', nucleus, 
                    satellite, conditions, 5)


    def genrule_compare_eval(self):
        '''Sequence(concession_books, {pos_eval, neg_eval, usermodel_match, 
        usermodel_nomatch})
        
        Meaning: 'concession_books' describes common and diverging features of 
        the books. 'pos_eval/neg_eval/usermodel_match/usermodel_nomatch' 
        explains how many user requirements they meet
        '''
        #TODO: split this rule? satellite=usermodel_match would actually 
        #require that there's no usermodel_nomatch, 
        #analogical: satellite=usermodel_nomatch 
        #book_differences = Contrast({id, id_extra_sequence}, lastbook_nomatch)
        #concession_books = Concession(book_differences, lastbook_match)
        nucleus = [('concession_books', 
                   ConstituentSet(satellite=Message('lastbook_match')))]
        satellite = [('pos_eval', ConstituentSet(satellite=Message('usermodel_nomatch'))), 
                     ('neg_eval', ConstituentSet(nucleus=Message('usermodel_nomatch'))), 
                     ('usermodel_match', Message('usermodel_match')), 
                     ('usermodel_nomatch', Message('usermodel_nomatch'))]
        conditions = []
        return Rule('compare_eval','Sequence', nucleus, satellite, 
                    conditions, 5)


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
        message_list = messages_instance_to_list_of_message_instances(messages)
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
