#!/usr/bin/env python
# -*- coding: utf-8 -*-

#TODO: fix Facts.generate_lastbook_facts: proglang values w/ set([]) should not generate facts

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
            if book.has_key("lastbook_facts"): # the 1st item doesn't have a preceding one...
                print book["lastbook_facts"]
    return facts

def gen_facts(arg):
    return Facts(Books(Results(Query(arg))))

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
        parser.add_argument("-s", "--pages", type=int,
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
        if args.pages:
            self.queries.append(self.pages_query(args.pages))
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
            self.page_range = 0
        elif self.pages >= 300 and self.pages < 600:
            self.page_range = 1
        elif self.pages >= 600:
            self.page_range = 2
            
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
        query_facts["usermodel_match"] = []
        query_facts["usermodel_nomatch"] = []
        query_args = self.query_args # safes me some typing ...

        if query_args.codeexamples:
            if query_args.codeexamples == book.codeexamples:
                query_facts["usermodel_match"].append(("codeexamples", query_args.codeexamples))
            else:
                query_facts["usermodel_nomatch"].append(("codeexamples", query_args.codeexamples))

        if query_args.exercises:
            if query_args.exercises == book.exercises:
                query_facts["usermodel_match"].append(("exercises", query_args.exercises))
            else:
                query_facts["usermodel_nomatch"].append(("exercises", query_args.exercises))

        if query_args.keywords:
            for keyword in query_args.keywords:
                print keyword
                if keyword in book.keywords:
                    query_facts["usermodel_match"].append(("keywords", keyword))
                else:
                    query_facts["usermodel_nomatch"].append(("keywords", keyword))
                
        if query_args.language:
            if query_args.language == book.language:
                query_facts["usermodel_match"].append(("language", query_args.language))
            else:
                query_facts["usermodel_nomatch"].append(("language", query_args.language))

        if query_args.pages:
            if query_args.pages == book.page_range:
                query_facts["usermodel_match"].append(("pages", query_args.pages))
            else:
                query_facts["usermodel_nomatch"].append(("pages", query_args.pages))
        
        if query_args.proglang: 
            for proglang in query_args.proglang:
                if proglang in book.proglang:
                    query_facts["usermodel_match"].append(("proglang", query_args.proglang))
                else:
                    query_facts["usermodel_nomatch"].append(("proglang", query_args.proglang))

        if query_args.target:
            if query_args.target == book.target:
                query_facts["usermodel_match"].append(("target", query_args.target))
            else:
                query_facts["usermodel_nomatch"].append(("target", query_args.target))
           
        return query_facts
                
    def generate_lastbook_facts(self, index, book, preceding_book):
        
        lastbook_facts = {}
        lastbook_facts["lastbook_match"] = []
        lastbook_facts["lastbook_nomatch"] = []

        if book.codeexamples == preceding_book.codeexamples:
            lastbook_facts["lastbook_match"].append(("codeexamples", book.codeexamples))
        else:
            lastbook_facts["lastbook_nomatch"].append(("codeexamples", book.codeexamples))

        if book.exercises == preceding_book.exercises:
            lastbook_facts["lastbook_match"].append(("exercises", book.exercises))
        else:
            lastbook_facts["lastbook_nomatch"].append(("exercises", book.exercises))

        lastbook_facts["lastbook_match"].append(("keywords", book.keywords.intersection(preceding_book.keywords))) # uses set intersection to check which keywords both books have in common
        lastbook_facts["lastbook_nomatch"].append(("keywords", book.keywords.symmetric_difference(preceding_book.keywords))) # set symmetric difference, checks which keywords are in the current but not the the preceding book OR which books are in preceding but not in the current book
        #NOTE: "keywords_current_book_only" and "keywords_preceding_book_only" were not part of JPolibox and might not be necessary
        lastbook_facts["lastbook_nomatch"].append(("keywords_current_book_only", book.keywords.difference(preceding_book.keywords))) #keywords that this book has but not the preceding one
        lastbook_facts["lastbook_nomatch"].append(("keywords_preceding_book_only", preceding_book.keywords.difference(book.keywords))) #keywords that the preceding book has but not the current one

        if book.language == preceding_book.language:
            lastbook_facts["lastbook_match"].append(("language", book.language))
        else:
            lastbook_facts["lastbook_nomatch"].append(("language", book.language))
            #TODO: should 'lastbook_nomatch' also contain preceding_book.language? or do we rant to get that from Books() when we generate document plans?

        if book.page_range == preceding_book.page_range:
            lastbook_facts["lastbook_match"].append(("page_range", book.page_range))
        else:
            if book.pages > preceding_book.pages:
                page_diff = book.pages - preceding_book.pages
                lastbook_facts["lastbook_nomatch"].append(("longer", page_diff))
            else: #current book is shorter
                page_diff = preceding_book.pages - book.pages
                lastbook_facts["lastbook_nomatch"].append(("shorter", page_diff))
        
        if book.proglang != set([]): #don't create a fact if the current book does not feature at lest one programming language
            if book.proglang.intersection(preceding_book.proglang) !=  set([]): # don't create a fact if the preceding book does not feat. at least 1 proglang
                lastbook_facts["lastbook_match"].append(("proglang", book.proglang.intersection(preceding_book.proglang)))
        lastbook_facts["lastbook_nomatch"].append(("proglang", book.proglang.symmetric_difference(preceding_book.proglang))) # symmetric difference never includes empty sets, so there's no need to check for them
        
        if book.target == preceding_book.target:
            lastbook_facts["lastbook_match"].append(("target", book.target))
        else:
            lastbook_facts["lastbook_nomatch"].append(("target", book.target))

        if book.year == preceding_book.year:
            lastbook_facts["lastbook_match"].append(("year", book.year))
        else:
            if book.year > preceding_book.year:
               years_diff = book.year - preceding_book.year 
               lastbook_facts["lastbook_nomatch"].append(("newer", years_diff))
            else:
                years_diff = preceding_book.year - book.year
                lastbook_facts["lastbook_nomatch"].append(("older", years_diff))
                
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
        pass

	#Propositions(Facts f): generates a Proposition() for each Fact()
	
	#if Fact() is of type:
		#UserModelMatch: setRating(Rating.Positive)
		#UserModelNoMatch: Rating.Negative
		#LastBookMatch: Rating.Neutral // why only neutral? b/c it's not related to usermodel
		#LastBookNoMatch: Rating.Neutral
		#Extra: if Year < 1990: setValue("< 1990")
			      #Year > 2000: setValue("< 2000")
			   #else:		   setRating(Rating.Neutral)
			   
	#idFacts() are handled differently:
    #they will processed to propostions only if there is no fact of other type with
    #the same property (Authors, Title, Keywords, Language, ProgLanguage, Pages, Year, TargetGroup, Exercises, Examples, UNDEFINED)
    
    #Example: If there is an Extra/UserModelMatch etc. Proposition about "Pages" (e.g. >= 600) or Year, there should be no ID Proposition about the same fact.
	
        #for (Fact fact : f) {
            #if (fact.getType() == Type.ID) {
                #boolean contains = false;
                #for (Proposition prop : this) {
                    #contains |= prop.getProperty() == fact.getProperty();
                #}
                #if (contains == false || fact.getProperty() == Property.Keywords) {
                    #add(new Proposition(fact));
                #}}}
	
	#why does this use "|=" aka "bitwise or"? http://www.roseindia.net/java/master-java/java-bitwise-or.shtml
		        
        
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
