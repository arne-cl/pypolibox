#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Arne Neumann <arne-neumann@web.de>

"""
The ``rules`` module contains rules, which are used by the text planner to
combine messages into constituent sets and ultimately form one ``TextPlan``.
"""

import itertools
import nltk
from nltk import Feature
from .messages import Message
from .util import exists

class ConstituentSet(nltk.featstruct.FeatDict):
    """
    ``ConstituentSet`` is the contstuction built up by applying ``Rules`` to a 
    set of ``ConstituentSet``s and ``Message``s. Each ``ConstituentSet`` is of a 
    specific ``relType``, and has two constituents, one which is designated the 
    ``nucleus`` and one which is designated ``aux``. These ``ConstituentSet``s can
    then be combined with other ``ConstituentSet``s or ``Message``s.

    ``ConstituentSet`` is based on ``nltk.featstruct.FeatDict``.
    """
    def __init__(self, relType = None, nucleus = None, satellite = None):
        """
        ``relType``, ``nucleus`` and ``aux`` are only specified for the 
        ``nltk.featstruct.FeatDict`` if they are specified by the user.

        :param relType: The relation type which related the ``nucleus`` to 
        ``aux``. 
        :type relType: string
        :param nucleus: Nucleus constituent. ``Message`` or ``ConstituentSet``.
        :type nucleus: Message or ConstituentSet
        :param satellite: Auxiliary constituent. ``Message`` or 
        ``ConstituentSet``. 
        :type satellite: Message or ConstituentSet
        """
        if relType: 
            self[nltk.featstruct.Feature('relType',display='prefix')] = relType
        if nucleus: 
            self[nltk.featstruct.Feature('nucleus',display='prefix')] = nucleus
        if satellite: 
            self[nltk.featstruct.Feature('satellite',display='prefix')] = satellite


class Rule(object):
    """
    ``Rules`` are the elements which specify relationships which hold between 
    elements of the document. These elements can be ``Message``s or 
    ``ConstituentSet``s.

    Each ``Rule`` specifies a list of ``inputs``, which are is a minimal 
    specification of a ``Message`` or ``ConstituentSet``. To be a valid input to 
    this Rule, a given ``Message`` or ``ConstituentSet`` must subsume one of the 
    specified ``input``s.

    Each ``Rule`` can also specify a set of conditions which must be met in 
    order for the Rule to hold between the inputs.

    Each ``Rule`` specifies a heuristic, which will be evaluated to provide a 
    score by which to rank the order in which rules should be applied.

    Each ``Rule`` specifies which of the inputs will be the ``nucleus`` and which
    will be the ``aux`` of the output ``ConstituentSet``.
    """

    def __init__(self, name, ruleType, nucleus, satellite, conditions, heuristic):
        """
        :param name: The name of the rule.
        :type name: string
        
        :param ruleType: The name of the relationship type this Rule specifies.
        :type ruleType: string
            
        :param conditions: a list of strings which will be evaluated as 
        conditions for applying the rule. These should return True or False 
        when evaluated
        :type conditions: list of strings
      
        :param nucleus: A list of tuples containing (name, input). ``name`` is 
        a string specifying the name used for the nucleus message of the RST 
        relation. The name is used to refer to this message in the 
        ``conditions`` and ``heuristic``. ``input`` is a ``Message`` or 
        ``ConstituentSet``. There can be only one nucleus in a RST relation, so 
        the planner has to choose from the list. 
        :type nucleus: list of tuples: (string, ``Message`` or 
        ``ConstituentSet``) 
      
        :param satellite: same as ``nucleus``, but represents a list of possible
        satellite messages of a RST relation. Again, there can be only one 
        satellite in a RST relation, so the planner has to choose from the 
        list. 
        
        :param heuristic: an integer used to rank potential ConstituentSets. 
        :type heuristic: ``int``
        """
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
        for (key, val) in self.__dict__.items():
            ret += str(key) + ' - ' + str(val) + '\n'
        return ret

    def get_options(self, messages):
        """
        this is the main method used for document planning 
            
        From the list of ``Messages``, ``get_options`` selects all possible ways 
        the Rule could be applied.

        The planner can then select with the :class:`textplan.__bottom_up_search` 
        function one of these possible applications of the Rule to use.
        
        ``non_empty_message_combinations`` is a list of combinations, where each
        combination is a (nucleus, satellite)-tuple. both the nucleus and the 
        satellite each consist of a (name, message) tuple.

        The method returns an empty list if ``get_options`` can't find a way 
        to apply the ``Rule``.

        :type messages: list of ``Message`` objects
        :param messages: a list of ``Message`` objects, each containing one 
        message about a book
        
        :rtype: empty list or a list containing one ``tuple`` of (``int``, 
        ``ConstituentSet``, ``list``), where ``list`` consists of ``Message`` 
        or ``ConstituentSet`` objects 
        :return: a list containing one 3-tuple (score, ``ConstituentSet``, 
        inputs) where: 
            - score is the evaluated heuristic score for this application of 
            the Rule 
            - ConstituentSet is the new ``ConstituentSet`` instance returned by 
            the application of the Rule
            - inputs is the list of inputs (``Message``s or ``ConstituentSets`` 
            used in this application of the rule 
        """
        self.messages = messages # will be used by self.__name_eval()
        nucleus_candidates = []
        satellite_candidates = []

        for message_prototype in self.nucleus:
            nucleus_candidates.extend(self.find_message_candidates(messages, 
                                                            message_prototype))

        for message_prototype in self.satellite:
            satellite_candidates.extend(self.find_message_candidates(messages,
                                                            message_prototype))
        
        # cartesian product (all possible combinations) 
        # of nucleus and satellite messages
        possible_msg_combinations = list(itertools.product(nucleus_candidates,  
                                                        satellite_candidates)) 
        
        condition_matching_combinations = self.get_satisfactory_groups(possible_msg_combinations) #remove messages which do not satisfy conditions
        
        non_empty_message_combinations = [msgs for msgs in condition_matching_combinations if msgs != [] ] # remove empty messages
 
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
        """
        takes a list of messages and returns only those with the right 
        message type (as specified in Rule.inputs)
        
        :type messages: ``list`` of ``Message``s
        :param messages: a list of ``Message`` objects, each containing one 
        message about a book

        :param message_prototype: a tuple consisting of a message name and a 
        ``Message`` or ``ConstituentSet``
        :type message_prototype: ``tuple`` of (string, ``Message`` or 
        ``ConstituentSet``)

        :rtype: ``list`` of ``tuple``s of (string, ``Message``)
        :return: a list containing all (name, message) tuples which are 
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
        """
        :type groups: ``list`` of ``list``'s of ``tuple``'s of (``str``, 
        ``Message`` or ``ConstituentSet``)
        :param groups: a list of group elements. each group contains a list 
        which contains one or more message tuples of the form 
        (message name, message)
        
        :rtype: ``list`` of ``list``'s of ``tuple``'s of (``str``, ``Message`` 
        or ``ConstituentSet``)
        :return: a list of group elements. contains only those groups which 
        meet all the conditions specified in self.conditions        
        """
        satisfactory_groups = []
        for group in groups:
            if all(self.get_conditions(group)):
                satisfactory_groups.append(group)
        return satisfactory_groups
        
    def get_conditions(self, group):
        """
        applies __name_eval to all conditions a Rule has, i.e. checks if a 
        group meets all conditions
        
        :type group: ``list`` of ``tuple``'s of (``str``, ``Message`` or 
        ``ConstituentSet``)
        :param group: a list of message tuples of the form 
        (message name, message)

        :rtype: ``list`` of ``bool``
        :return: a list of truth values, each of which tells if a group met 
        all conditions specified in self.conditions
        """
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
        """
        check if a ``condition`` is met by the ``Message``s in a ``group``
        
        :type condition: ``str``
        :param condition: a python statement that can be evaluated to True or 
        False, encoded as a string
        
        :type group: ``list`` of ``tuple``'s of (``str``, ``Message`` or 
        ``ConstituentSet``)
        :param group: a list of message tuples of the form 
        (message name, message)
        
        ``Message``s and ``ConstituentSet``s are ``FeatDict``s, which can be 
        queried just like normal ``dict``s.
        
        :rtype: ``bool``
        :return: True if the condition is met by the ``Message``s in ``group``
        """
        for message in self.messages:
            if Feature("msgType") in message: 
            #if it's a ``Message`` and not a ``ConstituentSet``
                message_name = message[Feature("msgType")]
                locals()[message_name] = message

        try:
            ret = eval(condition)
        except AttributeError:
            ret = False
        return ret

    def __get_return(self, combination):
        """
        constructs a ``ConstituentSet`` returned by ``get_options``

        :type combination: ``tuple`` of two ``tuple``s of (``str``, ``Message`` 
        or ``ConstituentSet``)
        :param combination: a tuple of two message tuples -- the first one 
        represents the nucleus, the second one the satellite -- of the form 
        (message name, message) that will be combined into a constituent set.

        :rtype: ``ConstituentSet``
        :return: a ``ConstituentSet``, which combines a nucleus and satellite. 
        both can either be a ``Message`` or ``ConstituentSet``
        """
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
        for name, rule in self.rule_dict.items():
            rule_summary = "{0}({1}, {2})".format(rule.ruleType, rule.nucleus,
                                                  rule.satellite)
            ret_str += "{0}: {1}\n\n".format(name, rule_summary)
            ret_str += "{0}\n\n".format(str(rule))
        return ret_str


    def genrule_id_extra_sequence(self):
        """Sequence(id_complete, extra), if 'extra' exists:
        
        adds an additional "sentence" about extra facts after the id messages"""
        nucleus = [('id', Message('id'))]
        satellite = [('extra', Message('extra'))]
        conditions = ['exists("extra", locals())']
        return Rule('id_extra_sequence', 'Sequence', nucleus, satellite, 
                    conditions, 10)
    
    def genrule_id_usermodelmatch(self):
        """Elaboration({id, id_extra_sequence}, usermodel_match), if there's no
        usermodel_nomatch
        
        Meaning: This book fulfills ALL your requirments. It was written in ...,
        contains these features ... and ... etc"""
        nucleus = [('id', Message('id')), 
                  ('id_extra_sequence', ConstituentSet(nucleus=Message('id')))] 
        satellite = [('usermodel_match', Message('usermodel_match'))]
        conditions = ['not exists("usermodel_nomatch", locals())']    
        return Rule('id_usermodelmatch', 'Elaboration', nucleus, satellite, 
                    conditions, 5)

    def genrule_pos_eval(self):
        """Concession(usermodel_match, usermodel_nomatch)
        
        Meaning: Book matches many (>= 50%) of the requirements, but not all of
        them"""
        nucleus = [('usermodel_match', Message('usermodel_match'))]
        satellite = [('usermodel_nomatch', Message('usermodel_nomatch'))]
        conditions = ['len(usermodel_match) >= len(usermodel_nomatch)'] 
        return Rule('pos_eval', 'Concession', nucleus, satellite,
                    conditions, 8)

    def genrule_neg_eval(self):
        """Concession(usermodel_nomatch, usermodel_match)
        
        Meaning: Although this book fulfills some of your requirements, it 
        doesn't match most of them. Therefore, this book might not be the best 
        choice."""
        nucleus = [('usermodel_nomatch', Message('usermodel_nomatch'))]
        satellite = [('usermodel_match', Message('usermodel_match'))]
        conditions = ['len(usermodel_match) < len(usermodel_nomatch)']
        return Rule('neg_eval', 'Concession', nucleus, satellite,
                    conditions, 8)

    def genrule_single_book_complete(self):
        """Sequence({id, id_extra_sequence}, {pos_eval, neg_eval})
        
        Meaning: The nucleus mentions all the (remaining) facts (that aren't 
        mentioned in the evaluation), while the satellite evaluates the book 
        (in terms of usermodel matches)
        """
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
        """Sequence({id, id_extra_sequence}, usermodel_match)
        
        Meaning: The satellite states that the book matches ALL the user's 
        requirements. The nucleus mentions the remaining facts about the book.
        Condition: there's no preceding book and there are only usermodel 
        matches.
        """
        nucleus = [('id', Message('id')), 
             ('id_extra_sequence', ConstituentSet(satellite=Message('extra')))]
        satellite = [('usermodel_match', Message('usermodel_match'))]
        conditions = ['not exists("usermodel_nomatch", locals())', 
                      'not exists("lastbook_match", locals())', 
                      'not exists("lastbook_nomatch", locals())']
        return Rule('single_book_complete_usermodelmatch', 'Sequence', nucleus,
                    satellite, conditions, 4)

    def genrule_single_book_complete_usermodelnomatch(self):
        """Sequence({id, id_extra_sequence}, usermodel_nomatch)
        
        Meaning: The satellite states that the book matches NONE of the user's 
        requirements. The nucleus mentions the remaining facts about the book.
        Condition: there's no preceding book and there are no usermodel 
        matches.
        """
        nucleus = [('id', Message('id')), 
             ('id_extra_sequence', ConstituentSet(satellite=Message('extra')))]
        satellite = [('usermodel_nomatch', Message('usermodel_nomatch'))]
        conditions = ['not exists("usermodel_match", locals())', 
                      'not exists("lastbook_match", locals())', 
                      'not exists("lastbook_nomatch", locals())']
        return Rule('single_book_complete_usermodelnomatch', 'Sequence', 
                    nucleus, satellite, conditions, 2)

    def genrule_book_differences(self):
        """Contrast({id, id_extra_sequence}, lastbook_nomatch)
        
        Meaning: id/id_extra_sequence. In contrast to book X, this book is in 
        German, targets advanced users and ...
        Condition: There are differences between the two books
        """
        nucleus = [('id', Message('id')), 
            ('id_extra_sequence', ConstituentSet(satellite=Message('extra')))]
        satellite = [('lastbook_nomatch', Message('lastbook_nomatch'))]
        conditions = ['exists("lastbook_nomatch", locals())']
        return Rule('book_differences', 'Contrast', nucleus, satellite, 
                    conditions, 5)

    def genrule_concession_books(self):
        """Concession(book_differences, lastbook_match)
        
        Meaning: After 'book_differences' explains the differences between both
        books, their common features are explained.
        """
        nucleus = [('book_differences', 
                   ConstituentSet(satellite=Message('lastbook_nomatch')))]
        satellite = [('lastbook_match', Message('lastbook_match'))]
        conditions = ['exists("lastbook_match", locals())']
        return Rule('concession_books', 'Concession', nucleus, satellite, 
                    conditions, 5)

    def genrule_concession_book_differences_usermodelmatch(self):
        """Concession(book_differences, usermodel_match)
        
        Meaning: 'book_differences' explains the differences between both books.
        Nevertheless, this book meets ALL your requirements ...
        Condition: All user requirements are met.
        """
        nucleus = [('book_differences', 
                    ConstituentSet(satellite=Message('lastbook_nomatch')))]
        satellite = [('usermodel_match', Message('usermodel_match'))]
        conditions = ['not exists("usermodel_nomatch", locals())']
        return Rule('concession_book_differences_usermodelmatch', 'Concession',
                    nucleus, satellite, conditions, 5)

    def genrule_book_similarities(self):
        """Elaboration(id_usermodelmatch, lastbook_match)
        
        Meaning: 'id_usermodelmatch' mentions that the books matches ALL 
        requirements. In addition, the book shares many features with its 
        predecessor.
        Condition: There are both differences and commonalities (>=50%) between
        the two books.
        """
        nucleus = [('id_usermodelmatch', 
                    ConstituentSet(satellite=Message('usermodel_match')))]
        satellite = [('lastbook_match', Message('lastbook_match'))] 
        conditions = ['exists("lastbook_match", locals())', 
                      'exists("lastbook_nomatch", locals())', 
                      'len(lastbook_match) >= len(lastbook_nomatch)']
        return Rule('book_similarities', 'Elaboration', nucleus, satellite, 
                    conditions, 5)

    def genrule_no_similarities_concession(self):
        #TODO: What's the connection between this rule and 'usermodel_(no)match'?
        """Concession({id, id_extra_sequence}, lastbook_nomatch)
        
        Meaning: Book X has these features BUT share none of them with its 
        predecessor.
        Condition: There is a predecessor to this book, but they don't share 
        ANY features.
        """
        nucleus = [('id', Message('id')), 
                   ('id_extra_sequence', ConstituentSet(satellite=Message('extra')))]
        satellite = [('lastbook_nomatch', Message('lastbook_nomatch'))]
        conditions = ['exists("lastbook_nomatch", locals())', 
                      'not exists("lastbook_match", locals())']
        return Rule('no_similarities_concession', 'Concession', nucleus, 
                    satellite, conditions, 5)


    def genrule_contrast_books_posneg_eval(self):
        #TODO: new-rules.rst rule 14 mentions that this one is only about 
        #books which share no features. WHY? 
        """Sequence(book_differences, {pos_eval, neg_eval})
        
        Meaning: book_differences mentions the differences between the books, 
        pos_eval/neg_eval explains how many user requirements they meet 
        Conditions: matches some of the requirements
        """
        nucleus = [('book_differences', 
                   ConstituentSet(satellite=Message('lastbook_nomatch')))]
        satellite = [('pos_eval', ConstituentSet(satellite=Message('usermodel_nomatch'))), 
                     ('neg_eval', ConstituentSet(nucleus=Message('usermodel_nomatch')))]
        conditions = ['exists("usermodel_match", locals())',
                      'exists("usermodel_nomatch", locals())'] 
                      #'not exists("lastbook_match", locals())'
        return Rule('contrast_books_posneg_eval', 'Sequence', nucleus, 
                    satellite, conditions, 5)


    def genrule_compare_eval(self):
        """Sequence(concession_books, {pos_eval, neg_eval, usermodel_match, 
        usermodel_nomatch})
        
        Meaning: 'concession_books' describes common and diverging features of 
        the books. 'pos_eval/neg_eval/usermodel_match/usermodel_nomatch' 
        explains how many user requirements they meet
        """
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
        return Rule('compare_eval', 'Sequence', nucleus, satellite, 
                    conditions, 5)

