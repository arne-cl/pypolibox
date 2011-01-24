#!/usr/bin/env python

#TODO: getopt: how to handle an option that has several arguments?
#              e.g. --keywords "pragmatics" "semantics"
#      alternatively, use the same option twice
#              e.g. -k "pragmatics" -k "semantics"

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
import getopt

db_file = "/home/guido/workspace/JPoliboxLocalNotebook/database/books.db"

# TABLE books (titel, year, authors, keywords, lang, plang, pages, target, exercises, examples);

usage = """
Please use at least one of the following parameters to query the database:

-k, --keyword
-l, --language
-p, --proglang
-e, --exercise
-c, --codeexamples
"""

conn = sqlite3.connect(db_file)
curs = conn.cursor()

#conn.commit() # commit changes to db
#conn.close() # close connection to db



def parse_commandline(argv):
    """
    parses commandline options to construct a database query, 
    sends the query and prints the results to stdout
    """
    queries = []
    try:
        opts, args = getopt.getopt(argv, "k:l:p:s:t:e:c:", ["keyword","language","proglang","pages","targetgroup","exercises","codeexamples"])
        print "opts:\n", opts
        print "args:\n", args
    except getopt.GetoptError:
        print usage
        sys.exit(2)
    if len(opts) == 0: #TODO: consult getopt manual, there has to be a better way
        print usage
        sys.exit(2)

    for opt, arg in opts: #TODO: right now ONLY ONE keyword is allowed!
        print "opt, args in opts:"
        print opt, arg
        if opt in ("-k", "--keywords"):       
            queries.append(substring_query("keywords", arg))
        if opt in ("-l", "--language"):
            queries.append(string_query("lang", arg))
        if opt in ("-p", "--proglang"):
            queries.append(string_query("plang", arg))
        if opt in ("-s", "--pages"):
            queries.append(pages_query(arg))
        if opt in ("-t", "--targetgroup"):
            # 0 beginner, 1 intermediate, 2 advanced, 3 professional
            #db fuckup: advanced is encoded as "3"
            queries.append(equals_query("target", arg))

        if opt in ("-e", "--exercises"):
            queries.append(equals_query("exercises", arg))
        if opt in ("-c", "--codeexamples"):
            queries.append(equals_query("examples", arg))


    print "The database will be queried for: {0}".format(queries)
    query = construct_commandline_query(queries)
    print "This query will be sent to the database: {0}".format(query)
    send_query(query)

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
    query_template = "SELECT * FROM books WHERE "
    print keywords, len(keywords)
    for key in keywords:
        sql_substring = "'%{0}%'".format(key)
        print "keywords like {0}".format(sql_substring)

def construct_commandline_query(queries):
    """takes a list of queries and combines them into one complex SQL query"""
    #query_template = "SELECT titel, year FROM books WHERE "
    query_template = "SELECT * FROM books WHERE "
    combined_queries = ""
    if len(queries) > 1:
        for query in queries[:-1]: # combine queries with " AND ", but don't append after the last query
            combined_queries += query + " AND "
        combined_queries += queries[-1]
    else: #nothing to combine here...
        combined_queries = queries[0] # list with one string element --> string
    
    print "query_template: {0} of type {1}".format(query_template, type(query_template))
    print "combined_queries: {0} of type{1}".format(combined_queries, type(combined_queries))
    return query_template + combined_queries

def send_query(query):
    query_result = curs.execute(query)
    for book in query_result:
        print book
    
def test_query():
    test_query = curs.execute('''select * from books where pages < 300;''')
    print "select * from books where pages < 300;\n\n"
    for result in test_query:
        print result


if __name__ == "__main__":
    parse_commandline(sys.argv[1:])

