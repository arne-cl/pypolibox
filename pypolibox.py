#!/usr/bin/env python
# -*- coding: utf-8 -*-


#TODO: it might be easier to encode those sqlite unicode strings as DEFAULT_ENCODING than to 
#      convert everything else to unicode!

#TODO: check why parser.add_argument isn't working correctly w/ type=int (if int = 0)

#TODO: sqlite: how to save query results for further examination?
#      alternatively, build a class structure for book items, ignoring SQL for further analysis

#DONE: check google books api to fill keywords:
#      http://books.google.com/books/feeds/volumes?q=0131873210 (search for an
#      ISBN)
# http://stackoverflow.com/questions/3287433/how-to-get-book-metadata
# http://code.google.com/p/gdata-python-client/

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
DB_FILE = 'books.db'
BOOK_TABLE_NAME = 'books' # name of the table in the database file that contains info about books

argv = ["-k", "pragmatics", "parsing"] #TODO: remove after debugging

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
        parser.add_argument("-s", "--pages",
            help="book length ranges. 0 = less than 300 pages, " \
                 "1 = between 300 and 600 pages. 2 = more than 600 pages.")
        parser.add_argument("-t", "--targetgroup",
            help="target audience. 0 = beginner, 1 = intermediate" \
                 "2 = advanced, 3 = professional")
        parser.add_argument("-e", "--exercises",
            help="Should the book contain exercises? 0 = no, 1 = yes")
        parser.add_argument("-c", "--codeexamples",
            help="Should the book contain code examples? 0 = no, 1 = yes")
        parser.add_argument("-r", "--minresults", #TODO: currently unused
            help="show no less than MINRESULTS books")
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
                self.queries.append(self.string_query("plang", proglang))
        if args.pages:
            self.queries.append(self.pages_query(args.pages))
        if args.targetgroup:
            # 0 beginner, 1 intermediate, 2 advanced, 3 professional
            #db fuckup: advanced is encoded as "3"
            assert args.targetgroup in ("0", "1", "2", "3")
            self.queries.append(self.equals_query("target", args.targetgroup))
        if args.exercises:
            assert args.exercises in ("0", "1",)
            self.queries.append(self.equals_query("exercises", args.exercises))
        if args.codeexamples:
            assert args.codeexamples in ("0", "1")
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
        assert length_category in ("0", "1", "2") # short, medium length, long books
        if length_category == "0":
            return "pages < 300"
        if length_category == "1":
            return "pages >= 300 AND pages < 600"
        if length_category == "2":
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
        and and stores the results in self.query_result
        
        @type q: instance of class C{Query}
        @param q: an instance of the class Query()
        """
        self.query_args = q.query_args # keep original queries for debugging
        
        conn = sqlite3.connect(DB_FILE)
        self.curs = conn.cursor() #TODO: i needed to "self" this to make it available in get_table_header(). it might be wise to move connect/cursor to the "global variables" part of the code.

        self.db_columns = self.get_table_header(BOOK_TABLE_NAME) #NOTE: this has to be done BEFORE the actual query, otherwise we'll overwrite the cursor!
        
        self.query_result = self.curs.execute(q.query)
    
    def print_results(self):
        """a method that prints all items of a query result to stdout"""
        #TODO: this method can only be run once, since it's a 'live' sql cursor
        for book in self.query_result:
            print book

    def get_table_header(self, table_name):
        """
        get the column names (e.g. title, year, authors) and their index from the books table of the db and return them as a dictionary.
        """
        table_info = self.curs.execute('PRAGMA table_info({0})'.format(table_name))
        db_columns = {}
        for index, name, type, notnull, dflt_value, pk in table_info:
            db_columns[index] = name.encode(DEFAULT_ENCODING)
        return db_columns


class Books:
    """ a Books() instance represents ALL books that were found by a database query """

    def __init__ (self, results):
        """
        @type query_result: C{Results}
        @param query_result: an instance of the class Results() containing the results from a database query

        This method generates a list of Book() instances (saved as self.books), each representing one book from a database query.
        """
        self.query_args =  results.query_args # original query arguments for debugging
        self.books = []
        for result in results.query_result:
            book_item = Book(result)
            self.books.append(book_item)


class Book:
    """ a Book() instance represents ONE book from a database query """
    def __init__ (self, db_item):
        """
        fill Book() instance w/ metadata from the db

        @type db_item: C{tuple}
        @param db_item: an item from the C{sqlite3.Cursor} object that contains
        the results from the db query.
        """
        self.title = db_item[col_index("titel")]
        self.year = int(db_item[col_index("year")])

        authors_array = db_item[col_index("authors")]
        self.authors = sql_array_to_set(authors_array)

        keywords_array = db_item[col_index("keywords")]
        self.keywords = sql_array_to_set(keywords_array)

        self.language = db_item[col_index("lang")]
        self.proglang = db_item[col_index("plang")]
        #TODO: proglang should be an "sql_array" (1 book w/ 2 programming languages),
        #      but there's only one book in the db that is handled that way
        #      all other plang columns in the db are "ordinary" strings (e.g. no '[' or ']')

        self.pages = int(db_item[col_index("pages")])
        self.target = int(db_item[col_index("target")])
        self.exercises = int(db_item[col_index("exercises")]) != 0 # 0 -> False, 1 -> True
        self.codeexamples = int(db_item[col_index("examples")]) != 0 # 0 -> False, 1 -> True

class Facts():
    """
    Facts() represents facts about a Books(), which is a list of Book() instances
    
    @type b: C{Books}
    @param b: an instance of the class Books
    """
    def __init__ (self, b):
        """ """
        self.query_args = b.query_args # originall query args for generating query_facts
        self.books = {}
        for index, book in enumerate(b.books):
            if index == 0: #first book
                book_facts = self.generate_facts(index, book)
                self.books[index] = book_facts
            else: # every other book --> trigger comparison with preceeding book
                preceeding_book = b.books[index-1]
                book_facts = self.generate_facts(index, book, preceeding_book)
                self.books[index] = book_facts
    
    def generate_facts(self, index, book, preceeding_book=False):
        """
        facts are ultimately retrieved from sqlite3, all strings encoded as <type 'unicode'>, not as <type 'str'>! in order to compare user queries of <type 'str'> to <type 'unicode'> strings from the database, we'll need to convert them.
        
        convert <type 'str'> to <type 'unicode'>: some_string.decode(DEFAULT_ENCODING)
        """
        
        facts = {}
                
        facts["id_facts"] = self.generate_id_facts(index, book)
        facts["query_facts"] = self.generate_query_facts(index, book)
        facts["extra_facts"] = self.generate_extra_facts(index, book)
        
        if preceeding_book == False: # if this is the first/only book            
            pass # DON't compare this book to a non-existent preceeding one
        else:
            facts["lastbook_facts"] = self.generate_lastbook_facts( index, book, preceeding_book) # generate additional facts, comparing the current with the preceeding book        
        return facts

    def generate_id_facts(self, index, book):
        """ 
        returns a dictionary of id facts about the current book 
        """
        
        id_facts = {}
        id_facts["title"] = book.title
        id_facts["authors"] = book.authors
        id_facts["keywords"] = book.keywords
        id_facts["language"] = book.language
        id_facts["proglang"] = book.proglang #empty string if not specified in db
        id_facts["pages"] = book.pages
        id_facts["year"] = book.year
        id_facts["target"] = book.target
        id_facts["exercises"] = book.exercises
        id_facts["codeexamples"] = book.codeexamples
        return id_facts
        
    def generate_query_facts(self, index, book):
        """ """
        query_facts = {}
        query_facts["usermodel_match"] = []
        query_facts["usermodel_nomatch"] = []
        query_args = self.query_args # typing laziness...

        if query_args.keywords:
            for keyword in query_args.keywords:
                print keyword
                if keyword.decode(DEFAULT_ENCODING) in book.keywords:
                    query_facts["usermodel_match"].append(("keywords", keyword))
                else:
                    query_facts["usermodel_nomatch"].append(("keywords", keyword))
                

        #if args.language:
            #self.queries.append(self.string_query("lang", args.language))
        #if args.proglang:
            #for proglang in args.proglang:
                #self.queries.append(self.string_query("plang", proglang))
        #if args.pages:
            #self.queries.append(self.pages_query(args.pages))
        #if args.targetgroup:
            ## 0 beginner, 1 intermediate, 2 advanced, 3 professional
            ##db fuckup: advanced is encoded as "3"
            #assert args.targetgroup in ("0", "1", "2", "3")
            #self.queries.append(self.equals_query("target", args.targetgroup))
        #if args.exercises:
            #assert args.exercises in ("0", "1",)
            #self.queries.append(self.equals_query("exercises", args.exercises))
        #if args.codeexamples:
            #assert args.codeexamples in ("0", "1")
            #self.queries.append(self.equals_query("examples", args.codeexamples))


        return query_facts
        
	#queryFacts: compares current book w/ query. Facts will only be built if queried!
		#adds a new Fact(Type.UserModelMatch, Property.Keywords, keywordsMatch) if a book keyword matches a query keyword.
		
		#same thing for Language, ProgLanguage, Exercises, Examples
		
		#number of pages: 3 ranges that could match (>= 1 && <= 300, >= 300 && <= 600, >= 600)
		
		#target groups: range from 0 to 3 (in our db)
			#if ((book.getTargetGroup() + 1) == (query.getTargetGroup())) #WTF +1 ???
		
		#if facts and queries don't match: add a UserModelNoMatch Fact()
        
    def generate_lastbook_facts(self, index, book, preceeding_book):
        pass
    
    def generate_extra_facts(self, index, book):
        pass
        

#TODO: move helper functions to utils.py; complete unfinished ones

def col_index(column):
    """
    returns the index of an sql column given its title
    
    """
    sql_columns = ["titel", "year", "authors", "keywords", "lang", "plang", "pages", "target", "exercises", "examples"]
    index = sql_columns.index(column)
    return index

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

#def construct_query(keywords=[]):
    #"""
    ##TODO: unfinished
    #query constructor for non-commandline interface (API, GUI, web etc.)
    #"""
    #query_template = "SELECT * FROM books WHERE "
    #print keywords, len(keywords)
    #for key in keywords:
        #sql_substring = "'%{0}%'".format(key)
        #print "keywords like {0}".format(sql_substring)


if __name__ == "__main__":
    #commandline_query = parse_commandline(sys.argv[1:])
    q = Query(sys.argv[1:])
    #q.parse_commandline(sys.argv[1:])
    results = Results(q)
    results.print_results()
