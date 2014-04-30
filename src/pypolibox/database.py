#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Arne Neumann <arne-neumann@web.de>

"""
The I{database} module is responsible for parsing the user's requirements
(both from command line options, as well as interactively from the Python
interpreter), transforming these requirements into an SQL query, querying the
sqlite database and returning the results.
"""

import os
import argparse
import sqlite3
import util

if __name__ == '__main__':
    DB_FILE = 'data/books.sqlite'
else:
    DB_FILE = os.path.join(os.path.dirname(__file__),'data/books.sqlite')

BOOK_TABLE_NAME = 'books' # name of the table in the database file that
                          # contains info about books
DEFAULT_ENCODING = 'UTF8'

class Query:
    """
    a C{Query} instance represents one user query to the database

    Queries can be made from the command line, as well as from the Python
    interpreter. From the command line, queries can be made using either
    abbreviated or long parameters. The following examples both query the
    database for books that contain code examples and deal with both semantics
    and parsing::

        python pypolibox.py -k semantics, parsing -c 1
        python pypolibox.py --keywords semantics, parsing --codeexamples 1

    When calling I{pypolibox.py} from within the Python interpreter, the same
    query can be made using the following command::

        Query(["-k", "semantics", "parsing", "-c", "1"])

    If you print the C{Query} instance (by using the I{print} command), it
    will return the SQL query that was constructed from the user input::

        SELECT * FROM books WHERE keywords like '%semantics%' AND keywords
        like '%parsing%' AND examples = 1

    TODO: This module talks directly to the database. To make it easier to
    adapt pypolibox to a different domain, an SQL abstraction layer (e.g.
    SQL Alchemy) should be used.
    """
    def __init__ (self, argv):
        """
        given a list of query arguments, this constructor parses commandline
        options with argparse, constructs a valid sql query and stores the
        resulting query strings in self.and_query (using boolean AND to
        combine the query arguments) and self.or_query (boolean OR).

        TODO: add max_textplans paramter --> generate only the X highest
              ranking books

        @param argv: a list of strings (either parsed from the command line
        or set programmatically)
        @type argv: C{list} of C{str}
        """
        self.queries = []
        self.minresults = 3
        query_and = " AND "
        query_or = " OR "

        parser = argparse.ArgumentParser()

        parser.add_argument("-k", "--keywords", nargs='+',
            help="Which topic(s) should the book cover?")
            #nargs='+' handles 1 or more args
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
        parser.add_argument("-x", "--xml", action="store_true",
            help="Don't generate text, just return text plans in XML format.")

        #TODO: put the if.args stuff into its own method (maybe useful, if
        # there's a WebQuery(Query) class
        args = parser.parse_args(argv)

        if args.keywords is not None:
            for keyword in args.keywords:
                self.queries.append(self.__substring_query("keywords",
                                                           keyword))
        if args.language is not None:
            self.queries.append(self.__string_query("lang", args.language))
        if args.proglang is not None:
            for proglang in args.proglang:
                self.queries.append(self.__substring_query("plang", proglang))
        if args.pagerange is not None:
            self.queries.append(self.__pages_query(args.pagerange))
        if args.target is not None:
            # confusion: in the db, advanced is encoded as "3"
            # --> blame JPolibox ;)
            target_error = """target should be: 0 (beginner), 1
            (intermediate), 2 (advanced) or 3 (professional)"""
            assert args.target in (0, 1, 2, 3), target_error
            self.queries.append(self.__equals_query("target", args.target))
        if args.exercises is not None:
            exercises_error = """exercises value should be either 0 (books
            should have no exercises) or 1 (book should have exercises)"""
            assert args.exercises in (0, 1), exercises_error
            self.queries.append(self.__equals_query("exercises",
                                                    args.exercises))
        if args.codeexamples is not None:
            codeexamples_error = """codeexamples value should be either 0
            (books should have no code examples) or 1 (book should have code
            examples)"""
            assert args.codeexamples in (0, 1), codeexamples_error
            self.queries.append(self.__equals_query("examples",
                                                    args.codeexamples))
        if args.minresults is not None:
            assert args.minresults > 0, """the minimal number of results must
            be 1"""
            self.minresults = args.minresults

        self.query_args = args # we may need these for debugging
        self.and_query = self.__construct_query(self.queries, query_and)
        self.or_query = self.__construct_query(self.queries, query_or)

    def __construct_query(self, queries, query_combinator):
        """
        helper function for __init__: takes a list of query arguments and
        combines them into one complex SQL query (using either boolean AND or
        boolean OR).

        @param queries: a list of queries in SQL notation
        @type queries: C{list} of C{str}

        @param query_combinator: a string that can be used to combine SQL
        queries, e.g. " AND " or " OR "
        @type query_combinator: C{str}

        @return: a complex SQL query
        @rtype: C{str}
        """
        query_template = "SELECT * FROM books "
        where = "WHERE "
        combined_queries = ""
        if len(queries) > 1:
            for query in queries[:-1]:
            #combine queries with " AND ", but don't append
            #after the last query
                combined_queries += query + query_combinator
            combined_queries += queries[-1]
            return query_template + where + combined_queries
        elif len(queries) == 1: # simple query, no combination needed
            query = queries[0] # list with one string element --> string
            return query_template + where + query
        else: #empty query
            return query_template # query will show all books in the db

    def __pages_query(self, length_category):
        """
        helper function for __init__: constructs a query for page ranges
        (e.g. the book should have less than 300 pages or between 300 and 600
        pages).

        @param length_category: an integer specifying the page range of the
        book (0: short, 1: medium length, 2: long)
        @type length_category: C{int}

        @return: a part of a simple SQL query, e.g. 'pages < 300'
        @rtype: C{str}
        """
        length_error = """length value should be either 0: short, 1: medium
            length or 2: long"""
        assert length_category in (0, 1, 2), length_error
        if length_category == 0:
            return "pages < 300"
        if length_category == 1:
            return "pages >= 300 AND pages < 600"
        if length_category == 2:
            return "pages >= 600"

    def __substring_query(self, sql_column, substring):
        """
        helper function for __init__: our database has a strange format that
        combines several values in the same string. For example, under the
        key 'keywords', there could be a value such as
        '[semantics][parsing][phonology]'. Therefore, we'll need to query for
        substrings, e.g. to find a book about 'semantics'.

        @param sql_column: the name of the column in the database we're
        querying, e.g. 'keywords'
        @type sql_column: C{str}

        @param substring: a string we're looking for, e.g. 'semantics'
        @type substring: C{str}

        @return: a part of a simple SQL query, e.g. 'keyword like %semantics%'
        @rtype: C{str}
        """
        # keyword --> '%keyword%' for SQL LIKE queries
        sql_substring = "'%{0}%'".format(substring)
        substring_query = "{0} like {1}".format(sql_column, sql_substring)
        return substring_query

    def __string_query(self, sql_column, string):
        """
        helper function for __init__: find all database items that completely
        match a string in a given column, e.g. WHERE lang = 'German'

        @param sql_column: the name of the column in the database we're
        querying, e.g. 'lang'
        @type sql_column: C{str}

        @param string: a string we're looking for, e.g. 'German'
        @type string: C{str}

        @return: a part of a simple SQL query, e.g. 'keyword like %semantics%'
        @rtype: C{str}
        """
        return "{0} = '{1}'".format(sql_column, string)

    def __equals_query(self, sql_column, integer):
        """
        helper function for __init__: find all database items that completely
        match an integer value in a given column, e.g. WHERE exercises = 1

        @return: a part of a simple SQL query, e.g. 'exercises = 1'
        @rtype: C{str}
        """
        return "{0} = {1}".format(sql_column, integer)

    def __str__(self):
        """
        If you print a C{Query} instance, it will return the query strings
        that will be send to the database.
        """
        ret_str = "The arguments (parsed from the command line): " + \
            "{0}\nhave resulted in the following SQL query:".format(self.query_args) + \
            "\n{0}\n\nIf the query should return less than ".format(self.and_query) + \
            "{0} book(s), this query will be used and ranked ".format(self.minresults) + \
            "according to the number of query parameter matches:\n{0}".format(self.or_query)
        return ret_str

class Results:
    """
    A C{Results} instance sends queries to the database, retrieves and stores
    the results.
    """

    def __init__ (self, query):
        """
        initialises a connection to the db, sends queries and stores results
        in self.query_results

        If the query (combining query parameters with boolean AND) returns
        less than query.minresults books, a different query will be sent
        (combining query parameters with boolean OR). In the latter case, a
        maximum score (possible_matches) will be calculated (how many query
        parameters does a result match). possible_matches will be used by
        a C{Books} instance to find the n-best matching books.

        @type query: instance of class C{Query}
        @param query: an instance of the class Query()
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

        # NOTE: this has to be done BEFORE the actual query,
        # otherwise we'll overwrite the cursor!
        self.db_columns = self.get_table_header(BOOK_TABLE_NAME)

        and_sql_cursor = self.curs.execute(self.and_query)
        for result in and_sql_cursor:
            self.and_query_results.append(result)
        if len(self.and_query_results) >= self.minresults:
            self.possible_matches = self.get_number_of_possible_matches()
            self.query_results = self.and_query_results
            self.query_type = 'and'

        # if 'AND query' doesn't return enough results ...
        # TODO: this 'else block' only needs to be executed if the and_query
        # has too few results AND that query consists of more than one
        # parameter -- otherwise, it won't improve results.
        else:
            or_sql_cursor = self.curs.execute(query.or_query)
            for result in or_sql_cursor:
                self.or_query_results.append(result)
            self.possible_matches = self.get_number_of_possible_matches()
            self.query_results = self.or_query_results
            self.query_type = 'or'
        conn.close() # close connection to sqlite db

    def get_number_of_possible_matches(self):
        """
        Counts the number of query paramters that I{could} be matched by books
        from the results set. The actual scoring of books takes place in
        I{Books.get_book_ranks()}.

        For example, if a query contains the parameters::

            keywords = pragmatics, keywords = semantics, language = German

        it means that a book could possible match 3 parameters
        (possible_matches = 3).

        @return: the number of possible matches
        @rtype: C{int}
        """
        possible_matches = 0
        self.params = [param for param in self.query_args.__dict__
                          if param is not 'minresults'
                          if self.query_args.__getattribute__(param) is not None]
        self.values = map(self.query_args.__getattribute__, self.params)

        for value in self.values:
            if type(value) == list:
                possible_matches += len(value)
            else:
                possible_matches += 1
        return possible_matches

    def get_table_header(self, table_name):
        """
        get the column names (e.g. title, year, authors) and their index from
        the books table of the db and return them as a dictionary.

        @param table_name: name of a database table, e.g. 'books'
        @type table_name: C{str}

        @return: a dictionary, which contains the names of the table columns
        as keys and their index as values
        @rtype: C{dict}, with C{str} keys and C{int} values
        """
        table_info = self.curs.execute('PRAGMA table_info({0})'.format(table_name))
        db_columns = {}
        for index, name, data_type, notnull, dflt_value, pk in table_info:
            db_columns[name.encode(DEFAULT_ENCODING)] = index
        return db_columns

    def __str__(self):
        """
        prints the number of results and if boolean AND or boolean OR has
        been used to gather at least self.minresults number of books

        @rtype: C{str}
        """
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
    a C{Books} instance stores I{all} books that were found by a database query
    as a list of C{Book} instances in I{self.books}
    """

    def __init__ (self, results):
        """
        This constructor generates a list of C{Book} instances (saved in
        I{self.books}), each representing one book retrieved from a database
        query. Additionally, this method will attach a score to each book
        (depending on the number of query parameters it matches) using the
        I{get_book_ranks()} method.

        @param results: a C{Results} instance containing the results from a
        database query
        @type results: C{Results}
        """
        # original query arguments for debugging
        self.query_args = results.query_args
        self.query_type = results.query_type
        self.books = []
        sorted_books = []

        for result in results.query_results:
            book_item = Book(result, results.db_columns, results.query_args)
            self.books.append(book_item)

        if self.query_type == 'and':
            #since all 'AND query' results match all query parameters,
            #their score will always be 1.0
            self.scores = [1.0 for book in range(len(self.books))]
        elif self.query_type == 'or':
            book_ranks = self.get_book_ranks(results.possible_matches)
            for (score, index) in book_ranks:
                sorted_books.append( (self.books[index], score) )
            #magic unzip / reverse zip function
            self.books, self.scores = zip(*sorted_books)

    def get_book_ranks(self, possible_matches):
        """
        ranks 'OR query' results according to the number of query parameters
        they match.

        @param possible_matches: the number of (meaningful) parameters of the
        query.
        @type possible_matches: C{int}

        @return: a list of tuples, where each tuple consists of the score of
        a book and its index in C{self.books}
        @rtype: C{list} of (C{float}, C{int}) tuples
        """
        scores = []
        for index, book in enumerate(self.books):
            score = float(book.book_matches) / float(possible_matches)
            scores.append( (score, index) )
        return sorted(scores, reverse=True) #best (highest) scores first

    def __str__(self):
        """
        prints the index, book score and database key value pairs about each
        book that the query returned.
        """
        return_string = ""
        # since all 'AND query' results match all query parameters,
        # the score is always 1.0
        if self.query_type == 'and':
            for index, book in enumerate(self.books):
                book_string = "index: {0}, score: 1.0\n{1}\n".format(index,
                                                                book.__str__())
                return_string += book_string
            return return_string
        elif self.query_type == 'or':
            for index, book in enumerate(self.books):
                book_string = "index: {0}, score: {1}\n{2}\n".format(index,
                                                            self.scores[index],
                                                            book.__str__())
                return_string += book_string
            return return_string

class Book:
    """
    a C{Book} instance represents I{one} book from a database query
    """
    def __init__ (self, db_item, db_columns, query_args):
        """
        Fills a C{Book} instance with metadata from the database. Typical
        book metadata will look like this::

            language:		English
            title:		Computational Linguistics. An Introduction.
            pagerange:		0
            query_args:		Namespace(codeexamples=None, exercises=None,
                            keywords=None, language=None, minresults=2,
                            pagerange=None, proglang=None, target=None)
            year:		1986
            codeexamples:		0
            proglang:		set([])
            exercises:		1
            book_matches:		0
            authors:		set(['Ralph Grishman'])
            keywords:		set(['generation', 'discourse', 'semantics',
                            'parsing'])
            pages:		193

        All key value pairs from the database are encoded from unicode
        to UTF8 and the number of query parameters that a book matches is
        calculated via I{get_number_of_book_matches()}.

        @param db_item: an item from the C{sqlite3.Cursor} object that contains
        the results from the db query.
        @type db_item: C{tuple}

        @param db_columns: a dictionary of table columns (e.g. title, authors)
        from the database
        @type db_columns: C{dict}

        @param query_args: a key/value store containing the original user query
        @type query_args: C{argparse.Namespace}
        """
        #needed for generating query facts later on
        self.query_args = query_args

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
        """
        calculates the number of query parameters that a book matches

        @rtype: C{int}
        """
        book_matches = 0
        simple_attributes = ['codeexamples', 'exercises', 'language',
                             'pagerange', 'target']

        # may contain more than 1 value
        complex_attributes = ['keywords', 'proglang']

        for simple_attrib in simple_attributes:
            if self.query_args.__getattribute__(simple_attrib) == getattr(self,
                                                                simple_attrib):
                book_matches += 1
        for complex_attrib in complex_attributes:
            if self.query_args.__getattribute__(complex_attrib) is not None:
                for value in self.query_args.__getattribute__(complex_attrib):
                    if value in getattr(self, complex_attrib):
                        book_matches += 1
        return book_matches

    def __str__(self):
        """
        prints the book metadata gathered from the database
        """
        return_string = ""
        for key, value in self.__dict__.iteritems():
            return_string += "{0}:\t\t{1}\n".format(key, value)
        return return_string

def get_column(column_name):
    """
    debugging: primitive db query that returns all the values stored in a
    column, e.g. get_column("title") will return all book titles stored in
    the database

    @type column_name: C{str}
    @rtype: C{list} of C{str}
    """
    conn = sqlite3.connect(DB_FILE)
    curs = conn.cursor()

    col_curs = curs.execute("PRAGMA table_info({0})".format(BOOK_TABLE_NAME))
    columns = [header[1] for header in col_curs]
    #print "available table columns: {0}\n".format(columns)
    results_cursor = curs.execute("select {0} from books".format(column_name))
    results = [result[0] for result in results_cursor]
    conn.close() # close connection to db
    return results
