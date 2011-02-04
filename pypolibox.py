#!/usr/bin/env python
# -*- coding: utf-8 -*-

#TODO: fix Facts.generate_lastbook_facts: keyword values should not contain ' ', e.g. set([' ', 'pragmatics']) 

#TODO: fix database db_item plang empty fuckup:
#      introduce sanity checks in sqlite? proglang is a string but must contain either         
#      nothing or at least a set of brackets '[]'
#      better way to store string arrays in sqlite? 
    #>>> f = gen_facts(["-l", "English"])
    
    #Traceback (most recent call last):
      #File "<pyshell#6>", line 1, in <module>
        #f = gen_facts(["-l", "English"])
      #File "pypolibox.py", line 48, in gen_facts
        #return Facts(Books(Results(Query(arg))))
      #File "pypolibox.py", line 216, in __init__
        #book_item = Book(result, results.db_columns)
      #File "pypolibox.py", line 241, in __init__
        #proglang_array = db_item[db_columns["plang"]].encode(DEFAULT_ENCODING)
    #AttributeError: 'NoneType' object has no attribute 'encode'

#TODO: maybe replace older/newer short/long w/ directive + measure (+/-/=, pages/age)

#TODO: scrape keywords from google book feeds
#      checked: the gbooks keywords are not part of the API
#TODO: how to query lang = ANY in SQLite?

import sqlite3
import sys
import argparse
import re # for "utils"

DEFAULT_ENCODING = 'utf-8' # sqlite stores strings as unicode, 
                           # but the user input is likely something else
                           # (e.g. 'latin-1' or 'utf-8')
                           # change this var if your terminal only supports ascii-based encodings
DB_FILE = 'pypolibox.sqlite'
BOOK_TABLE_NAME = 'books' # name of the table in the database file that contains info about books
CURRENT_YEAR = 2011 # TODO: read this from the OS. use this to check if a book is 'fairly recent' 

argv = [ ["-k", "pragmatics"], \
         ["-k", "pragmatics", "semantics"], \
         ["-l", "German"], \
         ["-l", "German", "-p", "Lisp"], \
         ["-l", "German", "-p", "Lisp", "-k", "parsing"], \
         ["-l", "English", "-s", "0", "-c", "1"], \
         ["-l", "English", "-s", "0", "-e", "1", "-k", "discourse"], \
        ] # list of possible query arguments for debugging purposes

def debug_facts(argv): 
    """debugging function to check if all facts are created correctly"""
    facts = []
    for arg in argv:
        tmp = Facts(Books(Results(Query(arg))))
        facts.append(tmp)
    
    for f in facts:
        print "\n\n========================================================="
        print f.query_args
        for book in f.books:
            print book['query_facts']
            #if book.has_key("lastbook_facts"): # the 1st item doesn't have a preceding one...
             #   print book["lastbook_facts"]
    return facts

def gen_facts(arg):
    return Facts(Books(Results(Query(arg))))

def gen_props(arg):
    return Propositions(Facts(Books(Results(Query(arg)))))
    
#conn.commit() # commit changes to db
#conn.close() # close connection to db. 
#               DON't do this before all results are stored in a Book() instance

class Query:
    """ a Query() instance represents one user query to the database """

    def __init__ (self, argv):
        """ 
        parses commandline options with argparse, constructs a valid sql query and stores the resulting query in self.query
        """

        self.queries = []
        
        parser = argparse.ArgumentParser()
        
        parser.add_argument("-k", "--keywords", nargs='+', help="Which topic(s) should the book cover?") #nargs='+' handles 1 or more args    
        parser.add_argument("-l", "--language",
            help="Which language should the book have?")
        parser.add_argument("-p", "--proglang", nargs='+',
            help="Which programming language(s) should the book use?")
        parser.add_argument("-s", "--pagerange", type=int,
            help="book length ranges. 0 = less than 300 pages, " \
                "1 = between 300 and 600 pages. 2 = more than 600 pages.")
        parser.add_argument("-t", "--target", type=int,
            help="target audience. 0 = beginner, 1 = intermediate" \
                 "2 = advanced, 3 = professional")
        parser.add_argument("-e", "--exercises", type=int,
            help="Should the book contain exercises? 0 = no, 1 = yes")
        parser.add_argument("-c", "--codeexamples", type=int,
            help="Should the book contain code examples? 0 = no, 1 = yes")
        parser.add_argument("-r", "--minresults", type=int,
            help="show no less than MINRESULTS books") #TODO: currently unused
            # minresults should trigger a fallback query to the db to get more results
            # e.g. combine the user's parameters with OR instead of AND:
            #       use some form of weigths to get the "best" results, e.g.
            #       keywords * 3 + language * 2 + other_parameters * 1
        
        #TODO: put the if.args stuff into its own method (maybe useful, if
        # there's a WebQuery(Query) class
        args = parser.parse_args(argv)
        print args
    
        if args.keywords:
            for keyword in args.keywords:
                self.queries.append(self.substring_query("keywords", keyword))
        if args.language:
            self.queries.append(self.string_query("lang", args.language))
        if args.proglang:
            for proglang in args.proglang:
                self.queries.append(self.substring_query("plang", proglang))
        if args.pagerange:
            self.queries.append(self.pages_query(args.pagerange))
        if args.target:
            # 0 beginner, 1 intermediate, 2 advanced, 3 professional
            #db fuckup: advanced is encoded as "3"
            assert args.target in (0, 1, 2, 3)
            self.queries.append(self.equals_query("target", args.target))
        if args.exercises:
            assert args.exercises in (0, 1,)
            self.queries.append(self.equals_query("exercises", args.exercises))
        if args.codeexamples:
            assert args.codeexamples in (0, 1)
            self.queries.append(self.equals_query("examples", args.codeexamples))
    
        print "The database will be queried for: {0}".format(self.queries)
        self.query_args = args # we may need these for debugging
        self.query = self.construct_query(self.queries)
        print "\nThis query will be sent to the database: {0}\n\n".format(self.query)


    def construct_query(self, queries):
        """takes a list of queries and combines them into one complex SQL query"""
        #query_template = "SELECT titel, year FROM books WHERE "
        query_template = "SELECT * FROM books "
        where = "WHERE "
        combined_queries = ""
        if len(queries) > 1:
            for query in queries[:-1]: # combine queries with " AND ", but don't append after the last query
                combined_queries += query + " AND "
            combined_queries += queries[-1]
            return query_template + where + combined_queries
        elif len(queries) == 1: # simple query, no combination needed
            query = queries[0] # list with one string element --> string
            print "type(queries): {0}, len(queries): {1}".format(type(queries), len(queries))
            return query_template + where + query
        else: #empty query
            return query_template # query will show all books in the db

    def pages_query(self, length_category):
        assert length_category in (0, 1, 2) # short, medium length, long books
        if length_category == 0:
            return "pages < 300"
        if length_category == 1:
            return "pages >= 300 AND pages < 600"
        if length_category == 2:
            return "pages >= 600"
    
    def substring_query(self, sql_column, substring):
        sql_substring = "'%{0}%'".format(substring) # keyword --> '%keyword%' for SQL LIKE queries
        substring_query = "{0} like {1}".format(sql_column, sql_substring)
        return substring_query
    
    def string_query(self, sql_column, string):
        """find all database items that completely match a string
           in a given column, e.g. WHERE lang = 'German' """
        return "{0} = '{1}'".format(sql_column, string)
    
    def equals_query(self, sql_column, string):
        return "{0} = {1}".format(sql_column, string)


class Results:
    """ a Results() instance represents the results of a database query """
    
    def __init__ (self, q):
        """
        initialises a connection to the db, sends an sql query to the db 
        and and stores the results in self.query_results
        
        @type q: instance of class C{Query}
        @param q: an instance of the class Query()
        """
        self.query_args = q.query_args # keep original queries for debugging
        
        conn = sqlite3.connect(DB_FILE)
        self.curs = conn.cursor() #TODO: i needed to "self" this to make it available in get_table_header(). it might be wise to move connect/cursor to the "global variables" part of the code.

        self.db_columns = self.get_table_header(BOOK_TABLE_NAME) #NOTE: this has to be done BEFORE the actual query, otherwise we'll overwrite the cursor!
        
        temp_results = self.curs.execute(q.query)
        self.query_results = []
        for result in temp_results:
            self.query_results.append(result) # temp_result is a LIVE SQL cursor, so we need to make the results 'persistent', e.g. by writing them to a list
    
    def print_results(self):
        """a method that prints all items of a query result to stdout"""
        #TODO: this method can only be run once, since it's a 'live' sql cursor
        for book in self.query_results:
            print book

    def get_table_header(self, table_name):
        """
        get the column names (e.g. title, year, authors) and their index from the books table of the db and return them as a dictionary.
        """
        table_info = self.curs.execute('PRAGMA table_info({0})'.format(table_name))
        db_columns = {}
        for index, name, type, notnull, dflt_value, pk in table_info:
            db_columns[name.encode(DEFAULT_ENCODING)] = index
        return db_columns


class Books:
    """ a Books() instance represents ALL books that were found by a database query """

    def __init__ (self, results):
        """
        @type results: C{Results}
        @param results: an instance of the class Results() containing the results from a database query

        This method generates a list of Book() instances (saved as self.books), each representing one book from a database query.
        """
        
        self.query_args =  results.query_args # original query arguments for debugging
        self.books = []
        for result in results.query_results:
            book_item = Book(result, results.db_columns)
            self.books.append(book_item)


class Book:
    """ a Book() instance represents ONE book from a database query """
    def __init__ (self, db_item, db_columns):
        """
        fill Book() instance w/ metadata from the db

        @type db_item: C{tuple}
        @param db_item: an item from the C{sqlite3.Cursor} object that contains
        the results from the db query.
        """
        self.title = db_item[db_columns["title"]].encode(DEFAULT_ENCODING)
        self.year = db_item[db_columns["year"]]

        authors_array = db_item[db_columns["authors"]].encode(DEFAULT_ENCODING)
        self.authors = sql_array_to_set(authors_array)

        keywords_array = db_item[db_columns["keywords"]].encode(DEFAULT_ENCODING)
        self.keywords = sql_array_to_set(keywords_array)

        self.language = db_item[db_columns["lang"]].encode(DEFAULT_ENCODING)
        
        proglang_array = db_item[db_columns["plang"]].encode(DEFAULT_ENCODING)
        self.proglang = sql_array_to_set(proglang_array)
        
        #TODO: proglang should be an "sql_array" (1 book w/ 2 programming languages),
        #      but there's only one book in the db that is handled that way
        #      all other plang columns in the db are "ordinary" strings (e.g. no '[' or ']')

        self.pages = db_item[db_columns["pages"]]
        if self.pages < 300:
            self.pagerange = 0
        elif self.pages >= 300 and self.pages < 600:
            self.pagerange = 1
        elif self.pages >= 600:
            self.pagerange = 2
            
        self.target = db_item[db_columns["target"]]
        self.exercises = db_item[db_columns["exercises"]]
        self.codeexamples = db_item[db_columns["examples"]]

class Facts():
    """
    Facts() represents facts about a Books(), which is a list of Book() instances
    
    @type b: C{Books}
    @param b: an instance of the class Books
    """
    def __init__ (self, b):
        """ """
        self.query_args = b.query_args # originall query args for generating query_facts
        self.books = []
        for index, book in enumerate(b.books):
            if index == 0: #first book
                book_facts = self.generate_facts(index, book)
                self.books.append(book_facts)
            else: # every other book --> trigger comparison with preceeding book
                preceding_book = b.books[index-1]
                book_facts = self.generate_facts(index, book, preceding_book)
                self.books.append(book_facts)
    
    def generate_facts(self, index, book, preceding_book=False):
        """
        facts are ultimately retrieved from sqlite3, all strings encoded as <type 'unicode'>, not as <type 'str'>! in order to compare user queries of <type 'str'> to <type 'unicode'> strings from the database, we'll need to convert them.
        
        convert <type 'str'> to <type 'unicode'>: some_string.decode(DEFAULT_ENCODING)
        """
        
        facts = {}
                
        facts["id_facts"] = self.generate_id_facts(index, book)
        facts["extra_facts"] = self.generate_extra_facts(index, book)
        facts["query_facts"] = self.generate_query_facts(index, book)
                
        if preceding_book == False: # if this is the first/only book            
            pass # DON't compare this book to a non-existent preceeding one
        else:
            facts["lastbook_facts"] = self.generate_lastbook_facts( index, book, preceding_book) # generate additional facts, comparing the current with the preceeding book        
        return facts

    def generate_id_facts(self, index, book):
        """ 
        returns a dictionary of id facts about the current book
        
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
        
    def generate_query_facts(self, index, book):
        """ generate facts that describes if a book matches (parts of) the query"""
        query_facts = {}
        query_facts["usermodel_match"] = {}
        query_facts["usermodel_nomatch"] = {}
        query_args = self.query_args # safes me some typing ...
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
                matching_values = []
                nonmatching_values = []
                for value in values:
                    if value in getattr(book, complex_attribute):
                        matching_values.append(value)
                    else:
                        nonmatching_values.append(value)
                    query_facts["usermodel_match"][complex_attribute] = matching_values
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
        extra_facts = {}
        if book.pages < 100:
            extra_facts["pages"] = "very short"
        if book.pages > 600:
            extra_facts["pages"] = "very long"
        if (CURRENT_YEAR - 10) < book.year: # newer than 10 years
            extra_facts["year"] = "recent"
        if (CURRENT_YEAR - 30) > book.year: # older than 30 years
            extra_facts["year"] = "old"
        
        return extra_facts

class Propositions():
    """ 
    represents proprositions (positive/negative/neutral ratings) generated from a Facts() instance
    """ 
    def __init__ (self, facts):
        """
        @type facts: I{Facts}
        """
        self.propostions = []
        for book in facts.books:
            book_propositions = self.generate_propositions(book)
            self.propostions.append(book_propositions)
            
    def generate_propositions(self, book):
        """
        returns a C{dict} of propositions for each book from an element of a Facts.books C{list}
        """
        propositions = {}
        propositions['usermodel_match'] = {}
        propositions['usermodel_nomatch'] = {}
        propositions['lastbook_match'] = {}
        propositions['lastbook_nomatch'] = {}
        propositions['extra'] = {}
        
        for attribute, value in book['query_facts']['usermodel_match'].iteritems():
            propositions['usermodel_match'][attribute] =  (value, 'positive')
        for attribute, value in book['query_facts']['usermodel_nomatch'].iteritems():
            propositions['usermodel_nomatch'][attribute] = (value, 'negative')
            
        if book.has_key('lastbook_facts'): # 1st book doesn't have this
            for attribute, value in book['lastbook_facts']['lastbook_match'].iteritems():
                propositions['lastbook_match'][attribute] =  (value, 'neutral') # neutral (not positive, since it's not related 2 usermodel)
            for attribute, value in book['lastbook_facts']['lastbook_nomatch'].iteritems():
                propositions['lastbook_nomatch'][attribute] = (value, 'neutral')
        
        if book['extra_facts'].has_key('year'):
            if book['extra_facts']['year'] == 'recent':
                propositions['extra']['year'] = (book['extra_facts']['year'], 'positive')
            elif book['extra_facts']['year'] == 'old':
                propositions['extra']['year'] = (book['extra_facts']['year'], 'negative')
                
        if book['extra_facts'].has_key('pages'):
            propositions['extra']['pages'] = (book['extra_facts']['pages'], 'neutral')

        for fact in book['id_facts']:
            pass
	#idFacts() are handled DIFFERENTLY:
    #they will processed to propostions only if there is no fact of other type with
    #the same property (Authors, Title, Keywords, Language, ProgLanguage, Pages, Year, TargetGroup, Exercises, Examples, UNDEFINED)
    
    #Example: If there is an Extra/UserModelMatch etc. Proposition about "Pages" (e.g. >= 600) or Year, there should be no ID Proposition about the same fact.
	
        return propositions
        
#TODO: move helper functions to utils.py; complete unfinished ones

def sql_array_to_set(sql_array):
    """
    books.db uses '[' and ']' tohandle attributes w/ more than one value:
    e.g. authors = '[Noam Chomsky][Alan Touring]'

    this function turns those multi-value strings into a set with separate values
    """
    item = re.compile("\[(.*?)\]")
    items = item.findall(sql_array)
    item_set = set()
    for i in items:
        item_set.add(i)
    return item_set

def test_sql():
    """a simple sql query example to play around with"""
    query_results = curs.execute('''select * from books where pages < 300;''')
    print "select * from books where pages < 300;\n\n"
    return query_results

def test_cli():
    """run several complex queries and print their results to stdout"""
    argvectors = [ ["-k", "pragmatics"], \
                   ["-k", "pragmatics", "semantics"], \
                   ["-l", "German"], \
                   ["-l", "German", "-p", "Lisp"], \
                   ["-l", "German", "-p", "Lisp", "-k", "parsing"], \
                   ["-l", "English", "-s", "0", "-c", "1"], \
                   ["-l", "English", "-s", "0", "-e", "1", "-k", "discourse"], \
                ]
    for argv in argvectors:
        book_list = Books(Results(Query(argv)))
        print "{0}:\n\n".format(argv)
        for book in book_list.books:
            print book.title, book.year


if __name__ == "__main__":
    #commandline_query = parse_commandline(sys.argv[1:])
    q = Query(sys.argv[1:])
    #q.parse_commandline(sys.argv[1:])
    results = Results(q)
    results.print_results()
