#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Arne Neumann <arne-neumann@web.de>

"""
The I{facts} module takes the information stored in C{Book} instances and 
converts them into attribute value matrices (C{Facts}). Furthermore, the 
module compares each book with its predecessor (e.g. book A is newer than book 
B and has code examples, while B is shorter and targets beginners ...). The 
insights gathered from these comparisons are also stored in C{Facts} 
instances.
"""

import datetime

class AllFacts():
    """
    Simply speaking, an C{AllFacts} instance contains all facts about all 
    books that were returned by a database query. More formally, it contains a 
    C{Facts} instance for each C{Book} in a C{Books} instance.
    
    In a C{Books} instance, all books returned by a database query are sorted 
    by the number of query parameters they match ('user model match') in 
    descending order. This means, that C{AllFacts} will contain facts about 
    the best-matching book, followed by facts about the second-best matching 
    book (including a comparison to the best matching one), followed by facts 
    about the third-best matching book (including a comparison to the second 
    one) etc.
    """
    def __init__ (self, b):
        """
        generates all facts for all books returned by a database query, i.e. a 
        C{Facts} instance for each C{Book} in a C{Books} instance. For a 
        hands-on description, see the C{Facts} documentation.
        
        @param b: a C{Books} instance, which contains all C{Book} instances 
        that were constructed from the database query results.
        @type b: C{Books}
        """
        self.query_args = b.query_args # original query args for generating query_facts
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
        """
        print the facts for each book
        """
        return_string = ""
        for index, book in enumerate(self.books):
            return_string += "facts about book #{0}:\n".format(index) + \
                             "--------------------\n" + \
                             "{0}\n\n".format(book)
        return return_string

class Facts():
    """
    A C{Facts} instance represents facts about a single book, but also 
    contains a comparison of that particular book with its predecessor. 
    """
    def __init__ (self, book, book_score, index=0, preceding_book=False):
        """
        Uses the facts/metadata retrieved from the sqlite3 database, and 
        generates facts in form of an attribute value matrix. The facts are 
        grouped logically. A C{Facts} instance basically consists of a 
        dictionary (stored in I{self.facts}) containing these four keys::
        
            (1) 'id_facts'
            (2) 'extra_facts'
            (3) 'query_facts'
            (4) 'lastbook_facts'

        Since this method is basically dealing with a list of C{Book} 
        instances, the first book's C{Facts} instance will not contain 
        'lastbook_facts', as there is no previous book in the list that it 
        could be compared to.

        @param book: a C{Book} instance
        @type book: C{Book}
        
        @param book_score: the score of the book that was calculated in 
        L{Books.get_book_ranks()}
        @type book_score: C{float}
        
        @param index: the index of the book in the C{Books} list of books
        @type index: C{int}
        
        @param preceding_book: if True, there is a book preceding this one 
        and both books will be compared
        @type preceding_book: C{bool}
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
        """
        generates a dictionary of id facts about the current book which will be 
        stored in I{self.facts["id_facts"]}. In contrast to other facts, 
        I{id_facts} are those kind of facts that can be directly retrieved 
        from the database (i.e. there is no comparison between books or 
        reasoning involved). The id_facts dictionary contains the following 
        keys::
        
            id_facts keys       database book table columns
            
            'authors'
            'codeexamples'      'examples'
            'exercises'
            'keywords'
            'language'          'lang'
            'pages'
            'proglang'          'plang'
            'target'
            'title'
            'year'

        The key names should be self-exlanatory. In those cases where they do 
        not exactly match their counterparts in the database, the 
        corresponding database table column name is given in the table above.

        @param index: the index of the book in the C{Books} list of books
        @type index: C{int}

        @param book: a C{Book} instance
        @type book: C{Book}

        @return: a dictionary with the keys described above
        @rtype: C{dict}
        """
        id_facts = {}
        attributes = ['authors', 'codeexamples', 'exercises', 'keywords', 
                      'language', 'pages', 'proglang', 'target', 'title', 
                      'year']
        
        for attribute in attributes:
            # Instead of writing lots of repetitive code like in JPolibox:
            #    id_facts["authors"] = book.authors
            #    id_facts["codeexamples"] = book.codeexamples ...
            # we will get all those book attributes at once (with I{getattr}) 
            # and turn them into dictionary items (via I{__setitem__}).
            book_attribute = getattr(book, attribute)
            id_facts.__setitem__(attribute, book_attribute)
                
        return id_facts
        
    def generate_query_facts(self, index, book, book_score):
        """
        generates facts that describes if a book matches (parts of) the query 
        (a.k.a the user model). a typical query_facts dictionary will look 
        like this::
        
            query_facts:
                usermodel_nomatch: {'codeexamples': 0}
                usermodel_match: {'exercises': 1, 'keywords': 
                                 set(['semantics', 'parsing']), 'language': 
                                 'German'} 
                book_score: 0.8

        The book described in this examples matches 80 % of the user 
        requirements (it contains exercises and deals with semantics and 
        parsing and is written in German) but does not contain code examples 
        (as was asked for by the user).
        
        @param index: the index of the book in the C{Books} list of books
        @type index: C{int}

        @param book: a C{Book} instance
        @type book: C{Book}

        @param book_score: the score of the book that was calculated in 
        L{Books.get_book_ranks()}
        @type book_score: C{float}
        
        @return: a dictionary that contains three keys, the I{book_score}, 
        the I{usermodel_match} as well as the I{usermodle_nomatch}. 
        'usermodel_match' contains all the features that were requested by 
        the user and are present in the book. 'usermodle_nomatch' contains 
        all features that were requested but are missing from the book.
        @rtype: C{dict}
        """
        query_facts = {}
        query_facts["book_score"] = book_score
        query_facts["usermodel_match"] = {}
        query_facts["usermodel_nomatch"] = {}
        query_args = book.query_args
        simple_attributes = ['codeexamples', 'exercises', 'language', 
                             'pagerange', 'target']
        complex_attributes = ['keywords', 'proglang'] 
        # complex attributes may contain more than 1 value
        
        for simple_attribute in simple_attributes:
            #if query_args has a non-empty value for this attrib
            if getattr(query_args, simple_attribute):
                if getattr(query_args, simple_attribute) == getattr(book, simple_attribute):
                    query_facts["usermodel_match"][simple_attribute] = getattr(book, simple_attribute)
                else:
                    query_facts["usermodel_nomatch"][simple_attribute] = getattr(book, simple_attribute) 
                    
        for complex_attribute in complex_attributes:
            # if query_args has at least one value for this attrib
            if getattr(query_args, complex_attribute): 
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
        """
        generates facts that compare the current book with the preceding one. 
        A typical example of a lastbook_facts dictionary would look like 
        this::
        
            lastbook_facts:
                lastbook_nomatch: 
                    {'language': 'German', 
                    'keywords_preceding_book_only': 
                        set(['pragmatics', 'chart parsing']), 
                    'keywords_current_book_only':
                        set([' ', 'grammar', 'language hierarchy', 'corpora', 
                            'syntax', 'morphology', 'left associative 
                            grammar']), 
                    'codeexamples': 0, 
                    'proglang': set(['Lisp']), 
                    'newer': 11, 
                    'keywords': 
                        set([' ', 'grammar', 'language hierarchy', 'corpora', 
                        'syntax', 'left associative grammar', 'morphology', 
                        'chart parsing', 'pragmatics']),
                    'proglang_preceding_book_only': 
                        set(['Lisp'])} 
                lastbook_match: 
                    {'exercises': 1, 'keywords': set(['semantics', 
                    'parsing']), 'target': 0, 'pagerange': 1}

        This method will calculate if is newer/older/shorter/longer than its 
        predecessor (if so, it will store the difference as an integer). For 
        keys that have sets as their values (I{keywords} and I{proglang}), 
        the resulting dictionary will list which values differed and which 
        were only present in either the preceding or the current book.
        
        @param index: the index of the book in the C{Books} list of books
        @type index: C{int}

        @param book: a C{Book} instance
        @type book: C{Book}
                
        @param preceding_book: if True, there is a book preceding this one 
        and both books will be compared
        @type preceding_book: C{bool}
        
        @return: a dictionary with two keys: I{lastbook_match} and 
        I{lastbook_nomatch}, which in turn are dictionaries themselves and 
        contain facts that are shared between the two books (lastbook_match) 
        or that differ between the two (lastbook_nomatch). 
        """
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
        """
        generates I{extra_facts}, if the current book is very new/old or very 
        short/long.

        @param index: the index of the book in the C{Books} list of books
        @type index: C{int}

        @param book: a C{Book} instance
        @type book: C{Book}
        
        @return: a dictionary that contains information about the recency and 
        length of a book
        @rtype: C{dict}
        """
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
        """prints the C{Facts} instance, but omits empty values"""
        signifiers_of_emptyness = [ [], {}, set() ] # lists, dicts, sets can be empty (we can't simply say "if val:", since this this would not only exclude emtpy lists/dicts/sets but also "0")
        return_string = ""
        for key, value in self.facts.iteritems():
            if value not in signifiers_of_emptyness:
                return_string += "\n{0}:\n".format(key)
                for attribute, val in value.iteritems():
                    if val not in signifiers_of_emptyness:
                        return_string += "\t{0}: {1}\n".format(attribute, val)
        return return_string
