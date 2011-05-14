#!/usr/bin/env python
# -*- coding: utf-8 -*-

# TODO: remove empty frozensets from message generation!

import sys
import datetime
from time import time
from database import Query, Results, Book, Books
from textplan import DocPlan, Message, ConstituentSet, Rule, generate_textplan
from nltk import FeatDict
from nltk.featstruct import Feature 
  

class AllFacts():
    """
    AllFacts() represents facts about a Books() instance, which is a list of Book() instances
    """
    def __init__ (self, b):
        """ 
        @type b: C{Books}
        @param b: an instance of the class Books        
        """
        self.query_args = b.query_args # originall query args for generating query_facts
        self.books = []
        self.book_scores = b.scores
        
        for index, book in enumerate(b.books):
            book_score = self.book_scores[index]
            if index == 0: #first book
                book_facts = Facts(book, book_score, index)
                self.books.append(book_facts)
            else: # every other book --> trigger comparison with preceeding book
                preceding_book = b.books[index-1]
                book_facts = Facts(book, book_score, index, preceding_book)
                self.books.append(book_facts)
                
    def __str__(self):
        return_string = ""
        for index, book in enumerate(self.books):
            return_string += "facts about book #{0}:\n".format(index) + \
                             "--------------------\n" + \
                             "{0}\n\n".format(book)
        return return_string

class Facts():
    """ Facts() represents facts about a single Book() instance """
    def __init__ (self, book, book_score, index=0, preceding_book=False):
        """
        facts are ultimately retrieved from sqlite3, where all strings are encoded as <type 'unicode'>, not as <type 'str'>! in order to compare user queries of <type 'str'> to <type 'unicode'> strings from the database, we'll need to convert them.
        
        convert <type 'str'> to <type 'unicode'>: some_string.decode(DEFAULT_ENCODING)
        """
        facts = {}
                
        facts["id_facts"] = self.generate_id_facts(index, book)
        facts["extra_facts"] = self.generate_extra_facts(index, book)
        facts["query_facts"] = self.generate_query_facts(index, book, book_score)
                
        if preceding_book == False: # if this is the first/only book            
            pass # DON't compare this book to a non-existent preceeding one
        else:
            facts["lastbook_facts"] = self.generate_lastbook_facts(index, book, preceding_book) # generate additional facts, comparing the current with the preceeding book        
        self.facts = facts

    def generate_id_facts(self, index, book):
        """ returns a dictionary of id facts about the current book
        
        instead of writing lots of repetitive code like in JPolibox:
        
            id_facts["authors"] = book.authors
            id_facts["codeexamples"] = book.codeexamples ...
            
        get all those book attributes at once (getattr) and turn them into dictionary items (__setitem__).
        """
        id_facts = {}
        attributes = ['authors', 'codeexamples', 'exercises', 'keywords', 'language', 'pages', 'proglang', 'target', 'title', 'year']
        
        for attribute in attributes:
            book_attribute = getattr(book, attribute)
            id_facts.__setitem__(attribute, book_attribute)
                
        return id_facts
        
    def generate_query_facts(self, index, book, book_score):
        """ generate facts that describes if a book matches (parts of) the query"""
        query_facts = {}
        query_facts["book_score"] = book_score
        query_facts["usermodel_match"] = {}
        query_facts["usermodel_nomatch"] = {}
        query_args = book.query_args
        simple_attributes = ['codeexamples', 'exercises', 'language', 'pagerange', 'target']
        complex_attributes = ['keywords', 'proglang'] # may contain more than 1 value
        
        for simple_attribute in simple_attributes:
            if getattr(query_args, simple_attribute): #if query_args has a non-empty value for this attrib
                if getattr(query_args, simple_attribute) == getattr(book, simple_attribute):
                    query_facts["usermodel_match"][simple_attribute] = getattr(book, simple_attribute)
                else:
                    query_facts["usermodel_nomatch"][simple_attribute] = getattr(book, simple_attribute) 
                    
        for complex_attribute in complex_attributes:
            if getattr(query_args, complex_attribute): # if query_args has at least one value for this attrib
                values = getattr(query_args, complex_attribute)
                matching_values = set()
                nonmatching_values = set()
                for value in values:
                    if value in getattr(book, complex_attribute):
                        matching_values.add(value)
                    else:
                        nonmatching_values.add(value)
                if matching_values != set(): # if not empty ...
                    query_facts["usermodel_match"][complex_attribute] = matching_values
                if nonmatching_values != set():
                    query_facts["usermodel_nomatch"][complex_attribute] = nonmatching_values

        return query_facts
                
    def generate_lastbook_facts(self, index, book, preceding_book):
        
        lastbook_facts = {}
        lastbook_facts['lastbook_match'] = {}
        lastbook_facts['lastbook_nomatch'] = {}
        simple_comparisons = ['codeexamples', 'exercises','language', 'target']
        set_comparisons = ['keywords', 'proglang']
        
        for simple_comparison in simple_comparisons:
            if getattr(book, simple_comparison) == getattr(preceding_book, simple_comparison):
                lastbook_facts['lastbook_match'][simple_comparison] = getattr(book, simple_comparison)
            else:
                lastbook_facts['lastbook_nomatch'][simple_comparison] = getattr(book, simple_comparison)
                
        for attribute in set_comparisons:
            current_attrib = getattr(book, attribute)
            preceding_attrib = getattr(preceding_book, attribute)
            if current_attrib == preceding_attrib == set([]):
                pass # nothing to compare
            else:
                shared_values = current_attrib.intersection(preceding_attrib)
                if shared_values != set([]):
                    lastbook_facts['lastbook_match'][attribute] = shared_values
                
                non_shared_values = current_attrib.symmetric_difference(preceding_attrib)
                lastbook_facts['lastbook_nomatch'][attribute] = non_shared_values
                
                current_only_values = current_attrib.difference(preceding_attrib)
                if current_only_values != set([]):
                    fact_name = attribute + '_current_book_only'
                    lastbook_facts['lastbook_nomatch'][fact_name] = current_only_values

                preceding_only_values = preceding_attrib.difference(current_attrib)
                if preceding_only_values != set([]):
                    fact_name = attribute + '_preceding_book_only'
                    lastbook_facts["lastbook_nomatch"][fact_name] = preceding_only_values
 
        if book.year == preceding_book.year:
            lastbook_facts["lastbook_match"]["year"] = book.year
        else:
            if book.year > preceding_book.year:
               years_diff = book.year - preceding_book.year 
               lastbook_facts["lastbook_nomatch"]["newer"] = years_diff
            else:
                years_diff = preceding_book.year - book.year
                lastbook_facts["lastbook_nomatch"]["older"] = years_diff

        if book.pagerange == preceding_book.pagerange:
            lastbook_facts["lastbook_match"]["pagerange"] = book.pagerange
        else:
            if book.pages > preceding_book.pages:
                page_diff = book.pages - preceding_book.pages
                lastbook_facts["lastbook_nomatch"]["longer"] = page_diff
            else: #current book is shorter
                page_diff = preceding_book.pages - book.pages
                lastbook_facts["lastbook_nomatch"]["shorter"] = page_diff
                
        return lastbook_facts
    
    def generate_extra_facts(self, index, book):
        """ compare current book w/ predefined values and generate facts"""
        current_year = datetime.datetime.today().year
        extra_facts = {}
        if book.pages < 100:
            extra_facts["pages"] = "very short"
        if book.pages > 600:
            extra_facts["pages"] = "very long"
        if (current_year - 10) < book.year: # newer than 10 years
            extra_facts["year"] = "recent"
        if (current_year - 30) > book.year: # older than 30 years
            extra_facts["year"] = "old"
        
        return extra_facts

    def __str__(self):
        """returns a string representation of a Facts() instance, but omits empty values"""
        signifiers_of_emptyness = [ [], {}, set() ] # lists, dicts, sets can be empty (we can't simply say "if val:", since this this would not only exclude emtpy lists/dicts/sets but also "0")
        return_string = ""
        for key, value in self.facts.iteritems():
            if value not in signifiers_of_emptyness:
                return_string += "\n{0}:\n".format(key)
                for attribute, val in value.iteritems():
                    if val not in signifiers_of_emptyness:
                        return_string += "\t{0}: {1}\n".format(attribute, val)
        return return_string        


class AllPropositions:
    """
    contains propositions about ALL the books that were listed in a query result
    """
    def __init__ (self, allfacts):
        """
        @type facts: I{AllFacts}
        """
        self.books = []
        for book in allfacts.books:
            self.books.append(Propositions(book))

    def __str__(self):
        return_string = ""
        for index, book in enumerate(self.books):
            return_string += "propositions about book #{0}:\n".format(index) + \
                             "----------------------------\n" + \
                             "{0}\n\n".format(book)
        return return_string
        
class Propositions():
    """ 
    represents propositions (positive/negative/neutral ratings) of a single book. Propositions() are generated from Facts() about a Book().
    """ 
    def __init__ (self, facts):
        """
        @type facts: I{Facts}
        """
        facts = facts.facts # a Facts() stores its facts in .facts; this line saves some typing

        self.book_score = facts['query_facts']['book_score']
        propositions = {}
        propositions['usermodel_match'] = {}
        propositions['usermodel_nomatch'] = {}
        propositions['lastbook_match'] = {}
        propositions['lastbook_nomatch'] = {}
        propositions['extra'] = {}
        propositions['id'] = {}
        
        for attribute, value in facts['query_facts']['usermodel_match'].iteritems():
            propositions['usermodel_match'][attribute] =  (value, 'positive')
        for attribute, value in facts['query_facts']['usermodel_nomatch'].iteritems():
            propositions['usermodel_nomatch'][attribute] = (value, 'negative')
            
        if facts.has_key('lastbook_facts'): # 1st book doesn't have this
            for attribute, value in facts['lastbook_facts']['lastbook_match'].iteritems():
                propositions['lastbook_match'][attribute] =  (value, 'neutral') # neutral (not positive, since it's not related 2 usermodel)
            for attribute, value in facts['lastbook_facts']['lastbook_nomatch'].iteritems():
                propositions['lastbook_nomatch'][attribute] = (value, 'neutral')
        
        if facts['extra_facts'].has_key('year'):
            if facts['extra_facts']['year'] == 'recent':
                propositions['extra']['year'] = (facts['extra_facts']['year'], 'positive')
            elif facts['extra_facts']['year'] == 'old':
                propositions['extra']['year'] = (facts['extra_facts']['year'], 'negative')
                
        if facts['extra_facts'].has_key('pages'):
            propositions['extra']['pages'] = (facts['extra_facts']['pages'], 'neutral')

        for fact in facts['id_facts']:
            already_used_propositions = self.__do_not_use_twice(propositions)
            if fact not in already_used_propositions:
                propositions['id'][fact] = (facts['id_facts'][fact], 'neutral')

        self.propositions = propositions
            
    def __do_not_use_twice(self, propositions):
        """generates the set of proposition attributes that have been used before
        
        (e.g. as usermodel propositions, lastbook propositions, extra propositions) and should therefore not be used again to generate id propositions
        
        Example: If there is an Extra/UserModelMatch etc. Proposition about "Pages" (e.g. >= 600) or Year, there should be no ID Proposition about the same fact.
        """
        attributes = set()
        for proposition_type in propositions.keys():
            attrib_list = propositions[proposition_type].keys()
            for attribute in attrib_list:
                attributes.add(attribute)
        return attributes

    def __str__(self):
        """returns a string representation of a Propositions() instance omitting empty values"""
        return_string = ""
        return_string += "book score: {0}\n".format(self.book_score)
        for key, value in self.propositions.iteritems():
            if value: # if value is not empty
                return_string += "\n{0}:\n".format(key)
                for attrib, val in value.iteritems():
                    if val:
                        return_string += "\t{0}: {1}\n".format(attrib, val)
        return return_string

class AllMessages:
    """
    represents all Messages generated from AllPropositions about all Books() that were returned by a query
    """
    def __init__ (self, allpropositions):
        """
        @type allpropositions: C{AllPropositions}
        @param allpropositions: a C{AllPropositions} class instance containing a list of C{Propositions} instances
        
        This will genenerate a C{Messages} instance (containing all C{Message}s about a book) for each C{Propositions} instance. It also adds a 'lastbook_title' and 'lastbook_author' to C{Message}s that compare the current and the preceding book
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
                    book.propositions[message_type]['lastbook_title'] = lastbook.propositions['id']['title']
                    book.propositions[message_type]['lastbook_authors'] = lastbook.propositions['id']['authors']
                self.books.append(Messages(book))

            
    def __str__(self):
        ret_str = ""
        for index, book in enumerate(self.books):
            ret_str += "book #{0} is described with these messages:\n".format(index) + \
                       "==========================================\n\n{0}".format(book)
        return ret_str

class Messages:
    """
    represents all Messages generated from Propositions() about a Book()
    """
    
    def __init__ (self, propositions):
        """reads propositions and calls message generation functions 
        
        @type propositions: C{Propositions}
        @param propositions: a C{Propositions} class instance
        """
        self.book_score = propositions.book_score
        self.propositions = propositions.propositions
        self.messages = {}

        for proposition_type in self.propositions.iterkeys():
            if self.propositions[proposition_type]: # don't generate a message if there are no propositions about its content (e.g. about 'extra')
                self.messages[proposition_type] = self.generate_message(proposition_type)

    def generate_message(self, proposition_type):
        message = Message(msgType = proposition_type)
        proposition_dict = self.propositions[proposition_type]
        simple_propositions = set(('id','lastbook_match', 'usermodel_match', 'usermodel_nomatch')) 
        # simple_propositions can be turned into messages without further 'calculations'
        
        if proposition_type in simple_propositions:
                for attrib in proposition_dict.iterkeys():
                    value, rating = proposition_dict[attrib]
                    if type(value) == set: 
                        #keywords, authors and proglangs are stored as sets, but we need frozensets (hashable) when creating rules and checking for duplicate messages
                        value = frozenset(value)
                    message.update({attrib: value})
    
        if proposition_type is 'extra':
            message = self.generate_extra_message(proposition_dict)
    
        if proposition_type is 'lastbook_nomatch':
            message = self.generate_lastbook_nomatch_message(proposition_dict)
    
        if message[Feature("msgType")] is not 'id':
            message = self.add_identification_to_message(message)

        return message
                             
    def generate_extra_message(self, proposition_dict):
        msg = Message(msgType='extra')
        for attrib in proposition_dict.iterkeys():
            if attrib == 'year':
                description, rating = proposition_dict['year']
                recency = FeatDict({'description': description, 'rating': rating})
                msg.update({'recency': recency})
            else:
                value, rating = proposition_dict[attrib]
                if type(value) == set: 
                    value = frozenset(value)
                msg.update({attrib: value})
        return msg 
        
    def generate_lastbook_nomatch_message(self, proposition_dict):
        msg = Message(msgType='lastbook_nomatch')
        for attrib in proposition_dict.iterkeys():
            if attrib == 'longer':
                pages, rating = proposition_dict['longer']
                magnitude = FeatDict({'number': pages, 'unit': 'pages'})
                length = FeatDict({'type': 'RelativeVariation', 'direction': '+', 'magnitude': magnitude})
                msg.update({'length': length})
            elif attrib == 'shorter':
                pages, rating = proposition_dict['shorter']
                magnitude = FeatDict({'number': pages, 'unit': 'pages'})
                length = FeatDict({'type': 'RelativeVariation', 'direction': '-', 'magnitude': magnitude})
                msg.update({'length': length})
            elif attrib == 'newer':
                years, rating = proposition_dict['newer']
                magnitude = FeatDict({'number': years, 'unit': 'years'})
                recency = FeatDict({'type': 'RelativeVariation', 'direction': '+', 'magnitude': magnitude})
                msg.update({'recency': recency})
            elif attrib == 'older':
                years, rating = proposition_dict['older']
                magnitude = FeatDict({'number': years, 'unit': 'years'})
                recency = FeatDict({'type': 'RelativeVariation', 'direction': '-', 'magnitude': magnitude})
                msg.update({'recency': recency})
            else:
                value, rating = proposition_dict[attrib]
                if type(value) == set: 
                    value = frozenset(value)
                msg.update({attrib: value})
        return msg

    def add_identification_to_message(self, message):
        for attrib in ('title', 'authors'):
            value, rating = self.propositions['id'][attrib]
            if type(value) == set: 
                value = frozenset(value)
            message.update({attrib: value})
        return message
        
    def __str__(self):
        ret_str = ""
        ret_str += "book score: {0}\n\n".format(self.book_score)
        for message in self.messages.iterkeys():
            if self.messages[message]:
                ret_str += "{0}\n\n".format(self.messages[message])
        return ret_str
        
class Rules:
    """creates Rule() instances
    
    Each rule of the form Rule(ruleType, inputs, conditions, nucleus, aux, heuristic) is generated by its own method. Important note: these methods have to adhere to a naming convention, i.e. begin with 'genrule_'; otherwise, self.__init__ will fail! 
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
            rule_summary = "{0}({1}, {2})".format(rule.ruleType, rule.nucleus, rule.satellite)
            ret_str += "{0}: {1}\n\n".format(name, rule_summary)
            ret_str += "{0}\n\n".format(str(rule))
        return ret_str

    #def __init__(self, name, ruleType, nucleus, satellite, conditions, heuristic):

    def genrule_id_extra_sequence(self):
        '''Sequence(id_complete, extra), if 'extra' exists:
        
        adds an additional "sentence" about extra facts after the id messages'''
        nucleus = [('id', Message('id'))]
        satellite = [('extra', Message('extra'))]
        conditions = ['exists("extra", locals())']
        return Rule('id_extra_sequence', 'Sequence', nucleus, satellite, conditions, 10)
    
    def genrule_id_usermodelmatch(self):
        '''Elaboration({id, id_extra_sequence}, usermodel_match), if there's no usermodel_nomatch
        
        Meaning: This book fulfills ALL your requirments. It was written in ..., contains these features ... and ... etc'''
        nucleus = [('id', Message('id')), ('id_extra_sequence', ConstituentSet(nucleus=Message('id')))] 
        satellite = [('usermodel_match', Message('usermodel_match'))]
        conditions = ['exists("usermodel_nomatch", locals()) is False']    
        return Rule('id_usermodelmatch', 'Elaboration', nucleus, satellite, conditions, 5)

    def genrule_pos_eval(self):
        '''Concession(usermodel_match, usermodel_nomatch)
        
        Meaning: Book matches many (>= 50%) of the requirements, but not all of them'''
        nucleus = [('usermodel_match', Message('usermodel_match'))]
        satellite = [('usermodel_nomatch', Message('usermodel_nomatch'))]
        conditions = ['len(usermodel_match) >= len(usermodel_nomatch)'] 
        return Rule('pos_eval','Concession', nucleus, satellite, conditions, 8)

    def genrule_neg_eval(self):
        '''Concession(usermodel_nomatch, usermodel_match)
        
        Meaning: Although this book fulfills some of your requirements, it doesn't match most of them. Therefore, this book might not be the best choice.'''
        nucleus = [('usermodel_nomatch', Message('usermodel_nomatch'))]
        satellite = [('usermodel_match', Message('usermodel_match'))]
        conditions = ['len(usermodel_match) < len(usermodel_nomatch)']
        return Rule('neg_eval','Concession', nucleus, satellite, conditions, 8)

    def genrule_single_book_complete(self):
        '''Sequence({id, id_extra_sequence}, {pos_eval, neg_eval})
        
        Meaning: The nucleus mentions all the (remaining) facts (that aren't mentioned in the evaluation), while the satellite evaluates the book (in terms of usermodel matches)
        '''
        nucleus = [('id', Message('id')), ('id_extra_sequence', ConstituentSet(satellite=Message('extra')))]
        satellite = [('pos_eval', ConstituentSet(satellite=Message('usermodel_nomatch'))), ('neg_eval', ConstituentSet(nucleus=Message('usermodel_nomatch')))]
        conditions = []
        return Rule('single_book_complete', 'Sequence', nucleus, satellite, conditions, 3)

    def genrule_single_book_complete_usermodelmatch(self):
        '''Sequence({id, id_extra_sequence}, usermodel_match)
        
        Meaning: The satellite states that the book matches ALL the user's requirements. The nucleus mentions the remaining facts about the book.
        Condition: there's no preceding book and there are only usermodel matches.
        '''
        nucleus = [('id', Message('id')), ('id_extra_sequence', ConstituentSet(satellite=Message('extra')))]
        satellite = [('usermodel_match', Message('usermodel_match'))]
        conditions = ['exists("usermodel_nomatch", locals()) is False', 'exists("lastbook_match", locals()) is False', 'exists("lastbook_nomatch", locals()) is False']
        return Rule('single_book_complete_usermodelmatch','Sequence', nucleus, satellite, conditions, 4)

    def genrule_single_book_complete_usermodelnomatch(self):
        '''Sequence({id, id_extra_sequence}, usermodel_nomatch)
        
        Meaning: The satellite states that the book matches NONE of the user's requirements. The nucleus mentions the remaining facts about the book.
        Condition: there's no preceding book and there are no usermodel matches.
        '''
        nucleus = [('id', Message('id')), ('id_extra_sequence', ConstituentSet(satellite=Message('extra')))]
        satellite = [('usermodel_nomatch', Message('usermodel_nomatch'))]
        conditions = ['exists("usermodel_match", locals()) is False', 'exists("lastbook_match", locals()) is False', 'exists("lastbook_nomatch", locals()) is False']
        return Rule('single_book_complete_usermodelnomatch', 'Sequence', nucleus, satellite, conditions, 2)

    def genrule_book_differences(self):
        '''Contrast({id, id_extra_sequence}, lastbook_nomatch)
        
        Meaning: id/id_extra_sequence. In contrast to book X, this book is in German, targets advanced users and ...
        Condition: There are differences between the two books
        '''
        nucleus = [('id', Message('id')), ('id_extra_sequence', ConstituentSet(satellite=Message('extra')))]
        satellite = [('lastbook_nomatch', Message('lastbook_nomatch'))]
        conditions = ['exists("lastbook_nomatch", locals()) is True']
        return Rule('book_differences','Contrast', nucleus, satellite, conditions, 5)

    def genrule_concession_books(self):
        '''Concession(book_differences, lastbook_match)
        
        Meaning: After 'book_differences' explains the differences between both books, their common features are explained.
        '''
        nucleus = [('book_differences', ConstituentSet(satellite=Message('lastbook_nomatch')))]
        satellite = [('lastbook_match', Message('lastbook_match'))]
        conditions = ['exists("lastbook_match", locals()) is True']
        return Rule('concession_books','Concession', nucleus, satellite, conditions, 5)

    def genrule_concession_book_differences_usermodelmatch(self):
        '''Concession(book_differences, usermodel_match)
        
        Meaning: 'book_differences' explains the differences between both books. Nevertheless, this book meets ALL your requirements ...
        Condition: All user requirements are met.
        '''
        nucleus = [('book_differences', ConstituentSet(satellite=Message('lastbook_nomatch')))]
        satellite = [('usermodel_match', Message('usermodel_match'))]
        conditions = ['exists("usermodel_nomatch", locals()) is False']
        return Rule('concession_book_differences_usermodelmatch','Concession', nucleus, satellite, conditions, 5)

    def genrule_book_similarities(self):
        '''Elaboration(id_usermodelmatch, lastbook_match)
        
        Meaning: 'id_usermodelmatch' mentions that the books matches ALL requirements. In addition, the book shares many features with its predecessor.
        Condition: There are both differences and commonalities (>=50%) between the two books.
        '''
        nucleus = [('id_usermodelmatch', ConstituentSet(satellite=Message('usermodel_match')))]
        satellite = [('lastbook_match', Message('lastbook_match'))] 
        conditions = ['exists("lastbook_match", locals()) is True', 'exists("lastbook_nomatch", locals()) is True', 'len(lastbook_match) >= len(lastbook_nomatch)']
        return Rule('book_similarities','Elaboration', nucleus, satellite, conditions, 5)

    def genrule_no_similarities_concession(self):
        #TODO: What's the connection between this rule and 'usermodel_(no)match'?
        '''Concession({id, id_extra_sequence}, lastbook_nomatch)
        
        Meaning: Book X has these features BUT share none of them with its predecessor.
        Condition: There is a predecessor to this book, but they don't share ANY features.
        '''
        nucleus = [('id', Message('id')), ('id_extra_sequence', ConstituentSet(satellite=Message('extra')))]
        satellite = [('lastbook_nomatch', Message('lastbook_nomatch'))]
        conditions = ['exists("lastbook_nomatch", locals()) is True', 'exists("lastbook_match", locals()) is False']
        return Rule('no_similarities_concession','Concession', nucleus, satellite, conditions, 5)


    def genrule_contrast_books_posneg_eval(self):
        #TODO: new-rules.rst rule 14 mentions that this one is only about books which share no features. WHY?
        '''Sequence(book_differences, {pos_eval, neg_eval})
        
        Meaning: book_differences mentions the differences between the books, pos_eval/neg_eval explains how many user requirements they meet
        Conditions: matches some of the requirements
        '''
        nucleus = [('book_differences', ConstituentSet(satellite=Message('lastbook_nomatch')))]
        satellite = [('pos_eval', ConstituentSet(satellite=Message('usermodel_nomatch'))), ('neg_eval', ConstituentSet(nucleus=Message('usermodel_nomatch')))]
        conditions = ['exists("usermodel_match", locals()) is True', 'exists("usermodel_nomatch", locals()) is True'] #'exists("lastbook_match", locals()) is False'
        return Rule('contrast_books_posneg_eval','Sequence', nucleus, satellite, conditions, 5)


    def genrule_compare_eval(self):
        '''Sequence(concession_books, {pos_eval, neg_eval, usermodel_match, usermodel_nomatch})
        
        Meaning: 'concession_books' describes common and diverging features of the books. 'pos_eval/neg_eval/usermodel_match/usermodel_nomatch' explains how many user requirements they meet
        '''
        #TODO: split this rule? satellite=usermodel_match would actually require that there's no usermodel_nomatch, analogical: satellite=usermodel_nomatch 
        #book_differences = Contrast({id, id_extra_sequence}, lastbook_nomatch)
        #concession_books = Concession(book_differences, lastbook_match)
        nucleus = [('concession_books', ConstituentSet(satellite=Message('lastbook_match')))]
        satellite = [('pos_eval', ConstituentSet(satellite=Message('usermodel_nomatch'))), ('neg_eval', ConstituentSet(nucleus=Message('usermodel_nomatch'))), ('usermodel_match', Message('usermodel_match')), ('usermodel_nomatch', Message('usermodel_nomatch'))]
        conditions = []
        return Rule('compare_eval','Sequence', nucleus, satellite, conditions, 5)


class DocumentPlans:
    """generates all C{DocumentPlan}s for an C{AllMessages} instance, i.e. one DocumentPlan for each book that is returned as a result of the user's database query"""
    
    def __init__ (self, allmessages):
        """ Class initialiser """
        rules = Rules().rules # generate all C{Rule}s that the C{Message}s will be checked against
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
            



#TODO: move helper/test functions to utils.py



testqueries = [ [],
         ["-k", "pragmatics"],
         ["-k", "pragmatics", "-r", "4"],
         ["-k", "pragmatics", "semantics"],
         ["-k", "pragmatics", "semantics", "-r", "7"],
         ["-l", "German"],
         ["-l", "German", "-p", "Lisp"],
         ["-l", "German", "-p", "Lisp", "-k", "parsing"],
         ["-l", "English", "-s", "0", "-c", "1"],
         ["-l", "English", "-s", "0", "-e", "1", "-k", "discourse"],
         ["-k", "syntax", "parsing", "-l", "German", "-p", "Prolog", "Lisp", "-s", "2", "-t", "0", "-e", "1", "-c", "1", "-r", "7"],
            ] # list of possible query arguments for debugging purposes

error_testqueries = [ ["-k", "cheeseburger"], # keyword does not exist
               ["-k", "Pragmatics"], # keyword does exist, but only in lower case
               ["-l", "Luxembourgish"], # db has no books in this language
               ["-l", "Luxembourgish", "-k", "syntax"],
               ["-l", "English", "German"], # our db only lists monolingual books
               ["-p", ""], # should list all books that have no programming language associated with them
               ["-t", "5"], # --target should be a numerical value (int) in range 0..3
               ["-t", "-2"],
               ["-t", "1.0"],
               ["-t", "4.6"],
               ["-t", "foobar"], # --target should be a numerical value
               ["-t", ""],
               ["-s", "5"], # --pagerange should be a numerical value (int) in range 0..2
               ["-s", "-2"],
               ["-s", "1.0"],
               ["-s", "4.6"],
               ["-s", "foobar"], # --pagerange should be a numerical value
               ["-s", ""],
               ["-e", "5"], # --exercises should be 0 or 1
               ["-e", "-2"],
               ["-e", "1.0"],
               ["-e", "4.6"],
               ["-e", "foobar"],
               ["-e", ""],
               ["-c", "5"], # --codeexamples should be 0 or 1
               ["-c", "-2"],
               ["-c", "1.0"],
               ["-c", "4.6"],
               ["-c", "foobar"],
               ["-c", ""],
               ["-r", "5"], # --minresults should be 0 or a positive integer
               ["-r", "-2"],
               ["-r", "1.0"],
               ["-r", "4.6"],
               ["-r", "foobar"],
               ["-r", ""],
        ] # list of (im)possible query arguments for debugging purposes. TODO: which ones behave unexpectedly?


if __name__ == "__main__":
    q = Query(sys.argv[1:])
    results = Results(q)
    print results
