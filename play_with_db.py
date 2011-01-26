#!/usr/bin/env python

#TODO: check why parser.add_argument isn't working correctly w/ type=int (if int = 0)

#TODO: sqlite: how to save query results for further examination?
#      alternatively, build a class structure for book items, ignoring SQL for further analysis

#DONE: check google books api to fill keywords:
#      http://books.google.com/books/feeds/volumes?q=0131873210 (search for an
#      ISBN)
# http://stackoverflow.com/questions/3287433/how-to-get-book-metadata
# http://code.google.com/p/gdata-python-client/
#
# checked: the gbooks keywords are not part of the API

#TODO: scrape keywords from google book feeds


#TODO: how to query lang = ANY in SQLite?

import sqlite3
import sys
import argparse
import re # for "utils"

parser = argparse.ArgumentParser()

db_file = "/home/guido/workspace/JPoliboxLocalNotebook/database/books.db"
# TABLE books (titel, year, authors, keywords, lang, plang, pages, target, exercises, examples);

conn = sqlite3.connect(db_file)
curs = conn.cursor()

#conn.commit() # commit changes to db
#conn.close() # close connection to db

def parse_commandline(argv):
    """
    parses commandline options to construct a database query,
    returns an sql query
    """
    queries = []
 
    parser.add_argument("-k", "--keywords", nargs='+', #nargs='+' handles 1 or more args
        help="Which topic(s) should the book cover?")
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
    parser.add_argument("-r", "--maxresults", #TODO: currently unused
        help="show no more than MAXRESULTS books")
 
    args = parser.parse_args()
    print args
    
    if args.keywords:
        for keyword in args.keywords:
            queries.append(substring_query("keywords", keyword))
    if args.language:
        queries.append(string_query("lang", args.language))
    if args.proglang:
        for proglang in args.proglang:
            queries.append(string_query("plang", proglang))
    if args.pages:
        queries.append(pages_query(args.pages))
    if args.targetgroup:
        # 0 beginner, 1 intermediate, 2 advanced, 3 professional
        #db fuckup: advanced is encoded as "3"
        assert args.targetgroup in ("0", "1", "2", "3")
        queries.append(equals_query("target", args.targetgroup))
    if args.exercises:
        assert args.exercises in ("0", "1",)
        queries.append(equals_query("exercises", args.exercises))
    if args.codeexamples:
        assert args.codeexamples in ("0", "1")
        queries.append(equals_query("examples", args.codeexamples))

    print "The database will be queried for: {0}".format(queries)
    query = construct_commandline_query(queries)
    print "\nThis query will be sent to the database: {0}\n\n".format(query)
    return query


def pages_query(length_category):
    assert length_category in ("0", "1", "2") # short, medium length, long books
    if length_category == "0":
        return "pages < 300"
    if length_category == "1":
        return "pages >= 300 AND pages < 600"
    if length_category == "2":
        return "pages >= 600"
     
def substring_query(sql_column, substring):
    sql_substring = "'%{0}%'".format(substring) # keyword --> '%keyword%' for SQL LIKE queries
    substring_query = "{0} like {1}".format(sql_column, sql_substring)
    return substring_query

def string_query(sql_column, string):
    """find all database items that completely match a string
       in a given column, e.g. WHERE lang = 'German' """
    return "{0} = '{1}'".format(sql_column, string)

def equals_query(sql_column, string):
    return "{0} = {1}".format(sql_column, string)

def construct_query(keywords=[]):
    """
    #TODO: unfinished
    query constructor for non-commandline interface (API, GUI, web etc.)
    """
    query_template = "SELECT * FROM books WHERE "
    print keywords, len(keywords)
    for key in keywords:
        sql_substring = "'%{0}%'".format(key)
        print "keywords like {0}".format(sql_substring)

def construct_commandline_query(queries):
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
        

def query_db(query):
    """send an sql query to the db and return the results"""
    query_result = curs.execute(query)
    #print "type(query_result): {0}".format(type(query_result))
    return query_result
    
def print_results(query_result):
    """print all items of a query result to stdout"""
    for book in query_result:
        print book

def test_query():
    """a simple sql query example to play around with"""
    test_query = curs.execute('''select * from books where pages < 300;''')
    print "select * from books where pages < 300;\n\n"
    for result in test_query:
        print result


    

class Book:
    """
    TABLE books 
    (titel, year, authors, keywords, lang, plang, pages, target, exercises, examples)
    """
    def __init__ (self, db_item):
        """ fill Book() instance w/ metadata from the db """
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
        
            
#TODO: move the following functions into pypolibox-utils

def col_index(column):
    """returns the index of an sql column given its title"""
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
    
if __name__ == "__main__":
    commandline_query = parse_commandline(sys.argv[1:])
    results = query_db(commandline_query)
    print_results(results)

