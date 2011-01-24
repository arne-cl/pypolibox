import gdata.books.service
import feedparser

service = gdata.books.service.BookService()
book_results = {}
#results = service.search_by_keyword(isbn='9783525265512')


##Legal Identifiers are listed below and correspond to their meaning
##at http://books.google.com/advanced_book_search:
##        all_words 
##        exact_phrase 
##        at_least_one 
##        without_words 
##        title
##        author
##        publisher
##        subject
##        isbn
##        lccn
##        oclc
##        seemingly unsupported:
##        publication_date: a sequence of two, two tuples:
##            ((min_month,min_year),(max_month,max_year))
##            where month is one/two digit month, year is 4 digit, eg:
##            (('1','2000'),('10','2003')). Lower bound is inclusive,
##            upper bound is exclusive


def title_search(search_title):
    results = service.search_by_keyword(title=search_title)
    res = results.ToString()
    feed = feedparser.parse(res)
    for item in feed.entries:
        print item.title # list book titles
    book_results[search_title] = feed

def save_to_pickle(object_name, file_name):
    """saves an object to a pickle file
    input: object name, pickle file name (as STRING)"""
    pickle_file = open(file_name, "w")
    pickle.dump(object_name, pickle_file)
    pickle_file.close()

def load_from_pickle(object_name, file_name):
    """loads an object from a pickle file into memory
       input: object name as STRING (as stored in pickle file), pickle file name (as STRING).
       output: object.
    """
    pickle_file = open(file_name, "r")
    object_name = pickle.load(pickle_file)
    pickle_file.close()
    return object_name
    

