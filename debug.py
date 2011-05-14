from database import Query, Results, Books
from pypolibox import AllFacts, AllPropositions
from textplan import Rules, AllMessages

#from pypolibox import curs # TODO: move stuff to database.py

## TODO: fixme
#def test_sql():
    #"""a simple sql query example to play around with"""
    #query_results = curs.execute('''select * from books where pages < 300;''')
    #print "select * from books where pages < 300;\n\n"
    #return query_results


                
def genprops(querynumber=10):
    return AllPropositions(AllFacts(Books(Results(Query(testqueries[querynumber])))))
    
def genmessages(booknumber=0, querynumber=10):
    am = AllMessages(AllPropositions(AllFacts(Books(Results(Query(testqueries[querynumber]))))))  
    for message in am.books[booknumber].messages.values(): message.freeze() #freeze messages, so Rule()s can be tested against them
    return am.books[booknumber].messages.values()
    
def gendocplans(querynumber):
    docplans = []
    rules = Rules().rules
    am = AllMessages(AllPropositions(AllFacts(Books(Results(Query(testqueries[querynumber]))))))
    #print len(am.books)
    for book in am.books:
        messages = book.messages.values()
        docplan = generate_textplan(messages, rules)
        print docplan
        docplans.append(docplan)
    return docplans
    
def test_all_docplans():
    all_docplans = []
    for argnumber, arg in enumerate(testqueries):
        print "generating DocPlans for the query:{0}\n".format(arg)
        docplans = gendocplans(argnumber)
        print "generated {0} DocPlans".format(len(docplans))
        for i, docplan in enumerate(docplans):
            if docplan == None:
                print "When using query argument {0}, no docplan could be generated for book {1}".format(arg, i)
        all_docplans.append(docplans)
    return all_docplans
 
def enumprint(obj):
    for index, item in enumerate(obj):
        print "{0}:\n{1}\n".format(index, item)

def msgtypes(messages):
    '''print message types / rst relation types, no matter which data structure is used to represent them'''
    if isinstance(messages, Messages):
        for i, message in enumerate(messages.messages.values()):
            print i, __msgtype_print(message)    
    elif isinstance(messages, list) : # if messages is a list of C{Message}/C{ConstituentSet} instances
        for i, message in enumerate(messages):
            print i, __msgtype_print(message)
    elif isinstance(messages, Message):
        print "Message: ", __msgtype_print(messages)
    elif isinstance(messages, DocPlan):
        print "DocumentPlan: ", __msgtype_print(messages["children"])
    elif isinstance(messages, ConstituentSet):
        print "ConstituentSet: ", __msgtype_print(messages)

                
def __msgtype_print(message):
    '''recursive helper function for msgtypes(), which prints message types and RST relation types'''
    if isinstance(message, Message):
        return message[Feature("msgType")]
    if isinstance(message, ConstituentSet):
        nucleus = __msgtype_print(message[Feature("nucleus")])
        reltype = message[Feature("relType")]
        satellite = __msgtype_print(message[Feature("satellite")])
        return "{0}({1}, {2})".format(reltype, nucleus, satellite)

def avm_print(docplan):
    #TODO: escape "_*"
    avm_str = ""
    header = "\begin{avm}\n\\[\n\n"
    footer = "\n\n\\]\n\end{avm}"
    content = __avm(docplan)
    avm_str += header + content + footer 
    return avm_str

def __avm(message):
    '''
    @type: C{Message} or C{ConstituentSet}
    '''
    if isinstance(message, Message):
        msg_content = ""
        msg_name = message[Feature("msgType")]
        keys = message.keys()
        keys.remove(Feature("msgType"))

        msg_content += "\\[\n"
        for key in keys:
            value = message[key]
            msg_content += "{0} & {1} \\\\\n".format(key, value)
        msg_content += "\n\\]"

        message = "{0}\t& {1}".format(msg_name, msg_content)
        return message
        
    if isinstance(message, ConstituentSet):
        rel_name = message[Feature("relType")]
        nucleus = __avm(message[Feature("nucleus")])
        satellite = __avm(message[Feature("satellite")])
        message = "{0}\t& \\[ {1} \n\n {2} \\]".format(rel_name, nucleus, satellite)
        return message
    
    if isinstance(message, DocPlan):
        message = __avm(message["children"])
        return message
    
    if isinstance(message, FeatDict):
        msg_content += "\\[\n"
        for key in keys:
            value = message[key]
            msg_content += "{0} & {1} \\\\\n".format(key, value)
        msg_content += "\n\\]"
        return msg_content
        

        
def abbreviate_textplan(textplan):
    if isinstance(textplan, DocPlan):
        textplan = __abbrev(textplan["children"])
        return DocPlan(children=textplan)
    if isinstance(textplan, ConstituentSet):
        reltype = textplan[Feature("relType")]
        nucleus = __abbrev(textplan[Feature("nucleus")])
        satellite = __abbrev(textplan[Feature("satellite")])
        return ConstituentSet(relType=reltype, nucleus=nucleus, satellite=satellite)
    if isinstance(textplan, Message):
        msgtype = textplan[Feature("msgType")]
        return Message(msgType=msgtype)
        
def find_applicable_rules(messages):
    '''debugging: find out which rules are directly (i.e. without forming ConstituentSets first) applicable to your messages'''
    if type(messages) is list: # check if messages is a list of Message() instances
        pass
    elif isinstance(messages, Messages): # or a single Messages() instance
        messages = messages.messages.values()
        
    for name, rule in Rules().rule_dict.iteritems():
        try:
            if rule.get_options(messages) != []:
                nucleus_candidates = [rulename for (rulename, msg) in rule.nucleus]
                satellite_candidates = [rulename for (rulename, msg) in rule.satellite]
                print "{0}: {1} - {2}, {3} - is directly applicable and results in \n\t{4}\n\n".format(name, rule.ruleType, nucleus_candidates, satellite_candidates, rule.get_options(messages))
        except:
            print "ERROR: Could not check if rule {0} is applicable. Possible solution: test if the rule's conditions are specified appropriately.\n\n".format(name)

        
def findrule(ruletype="", attribute="", value=""):
    '''debugging: find rules that have a certain ruleType and some attribute-value pair
    
    findrule("Concession", "nucleus", "usermodel_match") finds rules of type 'Concession' where rule.nucleus == 'usermodel_match'
    '''
    rules = Rules().rule_dict
    matching_rules = {}
    
    if ruletype == "":
        for index, (name, rule) in enumerate(rules.iteritems()):
            if getattr(rule, attribute) is value:
                print "rule {0} - {1}:\n{2}".format(index, name, rule)
                matching_rules[name] = rule
    elif attribute == "":
        for index, (name, rule) in enumerate(rules.iteritems()):
            if rule.ruleType is ruletype:
                print "rule {0} - {1}:\n{2}".format(index, name, rule)
                matching_rules[name] = rule
    else:
        for index, (name, rule) in enumerate(rules.iteritems()):
            if rule.ruleType is ruletype and getattr(rule, attribute) is value:
                print "rule {0} - {1}:\n{2}".format(index, name, rule)
                matching_rules[name] = rule
    return matching_rules

def apply_rule(messages, rule_name):
    '''debugging: take a rule and apply it to your list of messages. 
    
    the resulting C{ConstituentSet} will be added to the list, while the messages involved in its construction will be removed.
    repeat this step until you've found an erroneous/missing rule'''

    options = Rules().rule_dict[rule_name].get_options(messages)
    if options:
        for option in options:
            score, constitutent_set, removes = option
            messages.append(constitutent_set)
            for message in removes:
                messages.remove(message)
            for message in messages:
                message.freeze()
    else:
        print "Sorry, this rule could not be applied to your messages."

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

def test_cli(query_arguments=testqueries):
    """run several complex queries and print their results to stdout"""
    for arg in query_arguments:
        book_list = Books(Results(Query(arg)))
        print "{0}:\n\n".format(arg)
        for book in book_list.books:
            print book.title, book.year

