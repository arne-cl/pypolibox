#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import sqlite3
import util

#import locale
#language, encoding = locale.getlocale()
#DEFAULT_ENCODING = encoding # sqlite stores strings as unicode, but the user input is likely something else

DB_FILE = 'books.sqlite'
BOOK_TABLE_NAME = 'books' # name of the table in the database file that contains info about books
DEFAULT_ENCODING = 'UTF8'

class Query:
    """ a Query() instance represents one user query to the database """
    def __init__ (self, argv):
        """ 
        parses commandline options with argparse, constructs a valid sql query and stores the resulting queries (boolean AND, boolean OR) in self.and_query and self.or_query.
        """
        self.queries = []
        self.minresults = 10 #TODO: change value after debugging
        query_and = " AND "
        query_or = " OR "

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
            help="show no less than MINRESULTS books") 
        
        #TODO: put the if.args stuff into its own method (maybe useful, if
        # there's a WebQuery(Query) class
        args = parser.parse_args(argv)
        self.args = args #TODO: remove after debugging
            
        if args.keywords is not None:
            for keyword in args.keywords:
                self.queries.append(self.__substring_query("keywords", keyword))
        if args.language is not None:
            self.queries.append(self.__string_query("lang", args.language))
        if args.proglang is not None:
            for proglang in args.proglang:
                self.queries.append(self.__substring_query("plang", proglang))
        if args.pagerange is not None:
            self.queries.append(self.__pages_query(args.pagerange))
        if args.target is not None:
            # 0 beginner, 1 intermediate, 2 advanced, 3 professional
            #db fuckup: advanced is encoded as "3"
            assert args.target in (0, 1, 2, 3) #TODO: add exceptions to all asserts
            self.queries.append(self.__equals_query("target", args.target))
        if args.exercises is not None:
            assert args.exercises in (0, 1)
            self.queries.append(self.__equals_query("exercises", args.exercises))
        if args.codeexamples is not None:
            assert args.codeexamples in (0, 1)
            self.queries.append(self.__equals_query("examples", args.codeexamples))
        if args.minresults is not None:
            assert args.minresults > 0
            self.minresults = args.minresults 
    
        self.query_args = args # we may need these for debugging
        self.and_query = self.__construct_query(self.queries, query_and)
        self.or_query = self.__construct_query(self.queries, query_or)

    def __construct_query(self, queries, query_combinator):
        """takes a list of queries and combines them into one complex SQL query"""
        query_template = "SELECT * FROM books "
        where = "WHERE "
        combined_queries = ""
        if len(queries) > 1:
            for query in queries[:-1]: # combine queries with " AND ", but don't append after the last query
                combined_queries += query + query_combinator
            combined_queries += queries[-1]
            return query_template + where + combined_queries
        elif len(queries) == 1: # simple query, no combination needed
            query = queries[0] # list with one string element --> string
            #print "type(queries): {0}, len(queries): {1}".format(type(queries), len(queries))
            return query_template + where + query
        else: #empty query
            return query_template # query will show all books in the db

    def __pages_query(self, length_category):
        assert length_category in (0, 1, 2) # short, medium length, long books
        if length_category == 0:
            return "pages < 300"
        if length_category == 1:
            return "pages >= 300 AND pages < 600"
        if length_category == 2:
            return "pages >= 600"
    
    def __substring_query(self, sql_column, substring):
        sql_substring = "'%{0}%'".format(substring) # keyword --> '%keyword%' for SQL LIKE queries
        substring_query = "{0} like {1}".format(sql_column, sql_substring)
        return substring_query
    
    def __string_query(self, sql_column, string):
        """find all database items that completely match a string
           in a given column, e.g. WHERE lang = 'German' """
        return "{0} = '{1}'".format(sql_column, string)
    
    def __equals_query(self, sql_column, string):
        return "{0} = {1}".format(sql_column, string)

    def __str__(self):
        ret_str = "The arguments (parsed from the command line): " + \
            "{0}\nhave resulted in the following SQL query:".format(self.query_args) + \
            "\n{0}\n\nIf the query should return less than ".format(self.and_query) + \
            "{0} book(s), this query will be used and ranked ".format(self.minresults) + \
            "according to the number of query parameter matches:\n{0}".format(self.or_query)
        return ret_str

class Results:
    """ a Results() instance represents the results of a database query """
    
    def __init__ (self, query):
        """initialises a connection to the db, sends queries and stores results in self.query_results
        
        if the query (combining query parameters with boolean AND) returns less than query.minresults, a different query will be sent (combining query parameters with boolean OR). in the latter case, a maximum score (possible_matches) will be calculated (how many query parameters does a result match). possible_matches will be used by Books() to find the n-best matching books.
        
        @type q: instance of class C{Query}
        @param q: an instance of the class Query()
        """
        self.and_query_results = []
        self.or_query_results = []
        self.query_results = []
        self.query_args = query.query_args
        self.and_query = query.and_query
        self.or_query = query.or_query
        self.minresults = query.minresults
        self.possible_matches = 0
        
        conn = sqlite3.connect(DB_FILE)
        self.curs = conn.cursor()
        
        self.db_columns = self.get_table_header(BOOK_TABLE_NAME) #NOTE: this has to be done BEFORE the actual query, otherwise we'll overwrite the cursor!
        
        and_sql_cursor = self.curs.execute(self.and_query)
        for result in and_sql_cursor:
            self.and_query_results.append(result)
        if len(self.and_query_results) >= self.minresults:
            self.possible_matches = self.get_number_of_possible_matches(self.and_query_results)
            self.query_results = self.and_query_results
            self.query_type = 'and'
        else: # if 'AND query' doesn't return enough results ... TODO: this should only be executed if the and_query has too few results AND that query consists of more than one parameter -- otherwise, it won't improve results in this case.
            or_sql_cursor = self.curs.execute(query.or_query)
            for result in or_sql_cursor:
                self.or_query_results.append(result)
            self.possible_matches = self.get_number_of_possible_matches(self.or_query_results)
            self.query_results = self.or_query_results
            self.query_type = 'or'
            
    def get_number_of_possible_matches(self, query_results):
        """
        counts the number of query paramters that could be matched by books from the results set. 
        example: keywords = pragmatics, keywords = semantics, language = German --> possible_matches = 3
        """
        possible_matches = 0
        self.params = [param for param in self.query_args.__dict__
                          if param is not 'minresults'
                          if self.query_args.__getattribute__(param) is not None]
        self.values = map(self.query_args.__getattribute__, self.params)
        #self.items = zip(self.params, self.values)
        for value in self.values:
            if type(value) == list:
                possible_matches += len(value)
            else:
                possible_matches += 1                                    
        return possible_matches
        
    def get_table_header(self, table_name):
        """
        get the column names (e.g. title, year, authors) and their index from the books table of the db and return them as a dictionary.
        """
        table_info = self.curs.execute('PRAGMA table_info({0})'.format(table_name))
        db_columns = {}
        for index, name, type, notnull, dflt_value, pk in table_info:
            db_columns[name.encode(DEFAULT_ENCODING)] = index
        return db_columns

    def __str__(self):
        ret_str = "The query:\n{0}\n\nreturned ".format(self.and_query) + \
            "{0} result(s):\n\n".format(len(self.and_query_results))
        for book in self.and_query_results:
            ret_str += str(book) + "\n"
        if len(self.and_query_results) < self.minresults:
            ret_str += "\nLess than {0} queries were returned, ".format(self.minresults) + \
                "therefore the query had to be rephrased:\n{0}\n".format(self.or_query) + \
                "and returned these results:\n{0}".format(self.or_query_results)
        return ret_str

        
class Books:
    """
    a Books() instance represents ALL books that were found by a database query 
    as a list of Book() instances saved to self.books 
    """

    def __init__ (self, results):
        """
        @type results: C{Results}
        @param results: an instance of the class Results() containing the results from a database query

        This method generates a list of Book() instances (saved as self.books), each representing one book from a database query.
        """
        self.query_args = results.query_args # original query arguments for debugging
        self.query_type = results.query_type
        self.books = []
        sorted_books = []

        for result in results.query_results:
            book_item = Book(result, results.db_columns, results.query_args)
            self.books.append(book_item)
        
        if self.query_type == 'and': #since all 'AND query' results match all query parameters, there score will always be 1.0
            self.scores = [1.0 for book in range(len(self.books))]
        elif self.query_type == 'or':
            book_ranks = self.get_book_ranks(results.possible_matches)
            for (score, index) in book_ranks:
                sorted_books.append( (self.books[index], score) )
            self.books, self.scores = zip(*sorted_books) #magic unzip / reverse zip function
                 
    def get_book_ranks(self, possible_matches):
        """
        'OR query' results do not match all query parameters, therefore we'll need to rank them
        """
        scores = []
        for index, book in enumerate(self.books):
            score = float(book.book_matches) / float(possible_matches)
            scores.append( (score, index) )
        return sorted(scores, reverse=True) #best (highest) scores first

    def __str__(self):
        return_string = ""
        if self.query_type == 'and': #since all 'AND query' results match all query parameters, the score is always 1.0
            for index, book in enumerate(self.books):
                book_string = "index: {0}\n{1}\n".format(index, book.__str__())
                return_string += book_string
            return return_string
        elif self.query_type == 'or':
            for index, book in enumerate(self.books):
                book_string = "index: {0}, score: {1}\n{2}\n".format(index, self.scores[index],  book.__str__())
                return_string += book_string
            return return_string

class Book:
    """ a Book() instance represents ONE book from a database query """
    def __init__ (self, db_item, db_columns, query_args):
        """
        fill Book() instance w/ metadata from the db

        @type db_item: C{tuple}
        @param db_item: an item from the C{sqlite3.Cursor} object that contains
        the results from the db query.
        
        @type db_columns: C{dict}
        @param db_columns: a dictionary of table columns (e.g. title, authors) from the database
        
        @type query_args: C{argparse.Namespace}
        @param query_args: a key/value store containing the original user query
        """
        self.query_args = query_args #needed for generating query facts later on
        
        self.title = db_item[db_columns["title"]].encode(DEFAULT_ENCODING)
        self.year = db_item[db_columns["year"]]

        authors_array = db_item[db_columns["authors"]].encode(DEFAULT_ENCODING)
        self.authors = util.sql_array_to_set(authors_array)

        keywords_array = db_item[db_columns["keywords"]].encode(DEFAULT_ENCODING)
        self.keywords = util.sql_array_to_set(keywords_array)

        self.language = db_item[db_columns["lang"]].encode(DEFAULT_ENCODING)
        
        proglang_array = db_item[db_columns["plang"]].encode(DEFAULT_ENCODING)
        self.proglang = util.sql_array_to_set(proglang_array)
        
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
        self.book_matches = self.get_number_of_book_matches()

    def get_number_of_book_matches(self):
        book_matches = 0
        simple_attributes = ['codeexamples', 'exercises', 'language', 'pagerange', 'target']
        complex_attributes = ['keywords', 'proglang'] # may contain more than 1 value
        
        for simple_attrib in simple_attributes:
            if self.query_args.__getattribute__(simple_attrib) == getattr(self, simple_attrib):
                book_matches += 1
        for complex_attrib in complex_attributes:
            if self.query_args.__getattribute__(complex_attrib) is not None:
                for value in self.query_args.__getattribute__(complex_attrib):
                    if value in getattr(self, complex_attrib):
                        book_matches += 1
        return book_matches
        
    def __str__(self):
        return_string = ""
        for key, value in self.__dict__.iteritems():
            return_string += "{0}:\t\t{1}\n".format(key, value)
        return return_string

