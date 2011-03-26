import string, re
import nltk
import util
import itertools
#from inputs import *

#original author: Nicholas FitzGerald
#cf. "Open-Source Implementation of Document Structuring Algorithm for NLTK"

# filling feature structures using strings
#
#>>> print nltk.featstruct.FeatDict('TotalRainMsg[period=june]')
#[ *type* = 'TotalRainMsg' ]
#[ period = 'june'         ]
#
#>>> fd = nltk.featstruct.FeatDict('TotalRainMsg[period=[month=June, year=2010]]')
#>>> print fd
#[ *type* = 'TotalRainMsg'     ]
#[                             ]
#[ period = [ month = 'June' ] ]
#[          [ year  = 2010   ] ]
#
# after you've set at least the *type* of your FeatDict in string form:
# nltk.featstruct.FeatDict('TotalRainMsg'), you can add new features in form 
# of dictionaries
#
#>>> fd.update({'foo': 'bar'})
#>>> print fd
#[ *type* = 'TotalRainMsg'     ]
#[ foo    = 'bar'              ]
#[                             ]
#[ period = [ month = 'June' ] ]
#[          [ year  = 2010   ] ]
#
# unfortunately, this doesn't work this easy for complex structures.
#
#>>> f = nltk.FeatStruct('MessageName')
#>>> f1 = nltk.FeatDict([('month', 'june'), ('year', '1996')])
#>>> print f1 
#[ month = 'june' ]
#[ year  = '1996' ]
#>>> f.update([('period', f1)])
#>>> print f
#[ *type* = 'MessageName'      ]
#[                             ]
#[ period = [ month = 'june' ] ]
#[          [ year  = '1996' ] ]
#
# or simpler:
#>>> m = Message(msgType='MsgName') # aka nltk.FeatStruct('MsgName')
#>>> m['magnitude'] = nltk.FeatDict({'number': 4, 'unit': 'inches'})
#>>> m
#ID msg[magnitude=[number=4, unit='inches']]
#>>> print m
#[ *msgType* = 'ID msg'              ]
#[                                   ]
#[ magnitude = [ number = 4        ] ]
#[             [ unit   = 'inches' ] ]

def compare_options(rules, messages): #TODO: remove after debugging
    for i, rule in enumerate(rules):
        print "****BEGIN COMPARISON {0}******************".format(i)
        print "comparing old vs. new  for rule {0}".format(i)
        rule.get_options(messages)
        old = rule.after_alternative
        new = rule.after
        if old == new:
            print "\n\nSAME: old and new have the same value for rule {0}:".format(i)
            print "\ttype_group: {0}\n".format(old)
        else:
            print "\n\nDIFFERENT: old and new have different values for rule {0}".format(i)
            print "\told: ", old, "\n"
            print "\tnew: ", new, "\n"
        print "####END COMPARISON {0}##################\n\n".format(i)

class DocPlan(nltk.featstruct.FeatDict):
    """
    C{DocPlan} is the output of Document Planning. A DocPlan consists of an optional title and text, and a child I{ConstituentSet}.
    """
    def __init__(self, dtype = 'DocPlan', text = None, children = None):
        self[nltk.featstruct.Feature('type',display='prefix')] = 'DPDocument'
        self['title'] = nltk.featstruct.FeatDict({'type': dtype, 'text':text})
        self['children'] = children

class ConstituentSet(nltk.featstruct.FeatDict):
    """
    C{ConstituentSet} is the contstuction built up by applying C{Rules} to a set of C{ConstituentSet}s and C{Message}s. Each C{ConstituentSet} is of a specific I{relType}, and has two constituents, one which is designated the I{nucleus} and one which is designated I{aux}. These C{ConstituentSet}s can then be combined with other C{ConstituentSet}s or C{Message}s.

    C{ConstituentSet} is based on C{nltk.featstruct.FeatDict}.
    """
    def __init__(self, relType = None, nucleus = None, aux = None):
        """
        I{relType}, I{nucleus} and I{aux} are only specified for the C{nltk.featstruct.FeatDict} if they are specified by the user.

        @param relType: The relation type which related the I{nucleus} to I{aux}.
        @type relType: string
        @param nucleus: Nucleus constituent. C{Message} or C{ConstituentSet}.
        @type nucleus: Message or ConstituentSet
        @param aux: Auxiliary constituent. C{Message} or C{ConstituentSet}.
        @type aux: Message or ConstituentSet
        """
        if relType: 
            self[nltk.featstruct.Feature('relType',display='prefix')] = relType
        if nucleus: 
            self[nltk.featstruct.Feature('nucleus',display='prefix')] = nucleus
        if aux: 
            self[nltk.featstruct.Feature('aux',display='prefix')] = aux

class Message(nltk.featstruct.FeatDict):
    """
    C{Message}s are the primary information bearing units. They are contructed during the Content Selection stage of NLG which preceded Document Structuring.

    Each C{Message} has a I{msgType} which defines what type of message it is. In addition, C{Message}s can have any number of other features which contain the information the message conveys. These can either be simple features, or C{nltk.featstruct.FeatStruct}s.

    C{Message} is based on C{nltk.featstruct.FeatDict}.
    """
    def __init__(self, msgType = None):
        """
        I{msgType} is only specified for the C{nltk.featstruct.FeatDict} if it is specified by the user.
        """
        if msgType: 
            self[nltk.featstruct.Feature('msgType',display='prefix')] = msgType

class Rule(object):
    """
    C{Rules} are the elements which specify relationships which hold between elements of the document. These elements can be I{Message}s or I{ConstituentSet}s.

    Each I{Rule} specifies a list of I{inputs}, which are is a minimal specification of a C{Message} or C{ConstituentSet}. To be a valid input to this Rule, a given C{Message} or C{ConstituentSet} must subsume one of the specified I{input}s.

    Each I{Rule} can also specify a set of conditions which must be met in order for the Rule to hold between the inputs.

    Each I{Rule} specifies a heuristic, which will be evaluated to provide a score by which to rank the order in which rules should be applied.

    Each I{Rule} specifies which of the inputs will be the I{nucleus} and which will be the I{aux} of the output C{ConstituentSet}.
    """

    def __init__(self, ruleType, inputs, conditions, nucleus, aux, heuristic):
        """
        @param ruleType: The name of the relationship type this Rule specifies.
        @type ruleTupe: string
        @param inputs: A list of tuples containing (name, input), where I{name} is a string specifying the name used for the input in the conditions and heuristic, and where input is Message or ConstituentSet
        @type inputs: list of tuples: (string, C{Message} or C{ConstituentSet})
        @param conditions: a list of strings which will be evaluated as conditions for applying the rule. These should return True or False when evaluated
        @type conditions: list of strings
        @param nucleus: string specifying name of input used for nucleus
        @type nucleus: string
        @param aux: string specifying name of input used for aux
        @type aux: string
        @param heuristic: an integer used to rank potential ConstituentSets. 
        @type heuristic: C{int}
        """

        self.ruleType = ruleType
        self.inputs = inputs
        self.conditions = conditions
        self.nucleus = nucleus
        self.aux = aux
        self.heuristic = heuristic

    def __str__(self):
        """
        This is just a simple string output for the rule which is mainly used for debugging.
        """
        ret = ''
        for (key, val) in self.__dict__.items():
            ret += str(key) + ' - ' + str(val) + '\n'
        return ret

    def get_options(self, messages):
        """the main method used for document planning 
        
        From the list of C{Messages}, I{get_options} selects all possible ways the Rule could be applied.

        The planner can then select -- with the __bottom_up_search function -- one of these possible applications of the Rule to use.

        @type messages: list of C{Message} objects
        @param messages: a list of C{Message} objects, each containing one message about a book
        
        @rtype: empty list or a list containing one C{tuple} of (C{int}, C{ConstituentSet}, C{list}), where C{list} consists of C{Message} or C{ConstituentSet} objects 
        @return: a list containing one 3-tuple (score, C{ConstituentSet}, inputs}) where:
            score - is the evaluated heuristic score for this application of the Rule
            const_set - is the new C{ConstituentSet} returned by the application of the Rule
            inputs - is the list of inputs (C{Message}s or C{ConstituentSets} used in this application of the rule
            returns an empty list if I{get_options} can't find a way to to apply the I{Rule}.
        """
        name_list = [] # a list containing the inputs names in order
        type_groups = [] # a list where each index is a list of all the input Messages which are subsumed by the input proto-type 

        for (name, condition) in self.inputs:
            name_list.append(name)
            type_groups.append( self.type_groups_filter(messages, condition) )
                    
        groups = list(itertools.product(*type_groups)) #get all possible combinations of inputs (a list containing the cartesian product of all elements of type_groups)
        
        groups = filter(lambda x: len(x) == len(set(x)), groups) #remove groups which contain duplicates (necessary, since cartesian product produces duplicates)
        
        groups = map(lambda x: zip(name_list, x), groups) #match names to messages

        groups = self.get_satisfactory_groups(groups) #remove groups which do not satisfy conditions
        
        groups = [group for group in groups if group != [] ] # remove empty groups

        #print 'GROUPS:', groups, '\n' #TODO: remove after debugging
        self.groups = groups #TODO: remove after debugging
        
        options_list = []
        inputs = []
        for i, group in enumerate(groups):
            #score = self.__name_eval(self.heuristic, group) #fitzgerald: weird str -> int
            score = self.heuristic
            constituent_set = self.__get_return(group)
            for message_tuple in group: #a group might contain more than one message!
                name, message = message_tuple
                inputs.append(message)
            options_list.append( (score, constituent_set, inputs) )
        return options_list            

    def type_groups_filter(self, messages, condition):
        """
        takes a list of messages and returns only those with the right message type (as specified in Rule.inputs)
        
        @type messages: C{list} of C{Message}s
        @param messages: a list of C{Message} objects, each containing one message about a book

        @param inputs: a C{Message} or C{ConstituentSet}
        @type inputs: C{Message} or C{ConstituentSet}

        @rtype: C{list} of C{Message}s
        @return: a list containing all messages which are subsumed by the input message type (self.inputs) -- if a rule should only be applied to UserModelMatch and UserModelNoMatch messages, the return value contains a list of messages with these types. 
        """
        messages_list = []
        for message in messages:
            if condition.subsumes(message):
                messages_list.append(message)
        return messages_list
        
    def get_satisfactory_groups(self, groups):    
        '''
        @type groups: C{list} of C{list}'s of C{tuple}'s of (C{str}, C{Message} or C{ConstituentSet})
        @param groups: a list of group elements. each group contains a list which contains one or more message tuples of the form (message name, message)
        
        @rtype: C{list} of C{list}'s of C{tuple}'s of (C{str}, C{Message} or C{ConstituentSet})
        @return: a list of group elements. contains only those groups which meet all the conditions specified in self.conditions        
        '''
        satisfactory_groups = []
        for group in groups:
            if all(self.get_conditions(group)) is True:
                satisfactory_groups.append(group)
        return satisfactory_groups
        
    def get_conditions(self, group):
        '''applies __name_eval to all conditions a Rule has, i.e. checks if a group meets all conditions
        
        @type group: C{list} of C{tuple}'s of (C{str}, C{Message} or C{ConstituentSet})
        @param group: a list of message tuples of the form (message name, message)

        @rtype: C{list} of C{bool}
        @return: a list of truth values, each of which tells if a group met all conditions specified in self.conditions
        '''
        results = []
        for condition in self.conditions:
            results.append( self.__name_eval(condition, group) )
        return results
                
    def __name_eval(self, condition, group):
        '''Evaluate if I{condition} is met by the C{message}s in I{group}
        
        @type condition: C{str}
        @param condition: a python statement that can be evaluated to True or False, encoded as a string
        
        @type group: C{list} of C{tuple}'s of (C{str}, C{Message} or C{ConstituentSet})
        @param group: a list of message tuples of the form (message name, message)
        
        C{Message}s and C{ConstituentSet}s are C{FeatDict}s, which can be queried just like normal C{dict}s.
        
        @rtype: C{bool}
        @return: True if the condition is met by the C{Message}s in I{group}
        
        Example:
        condition1: "M1.get(('attribute', 'direction')) == M2.get(('attribute', 'direction'))"
        group1 contains two message tuples: 
            ('M1', MonthlyRainfallMsg[attribute=[direction='+', magnitude=[number=2, unit='inches'], type='RelativeVariation'], period=[month=6, year=1996]]), 
            ('M2', TotalRainfallMsg[attribute=[direction='+', magnitude=[number=4, unit='inches'], type='RelativeVariation'], period=[month=6, year=1996]])                

        After adding the messages 'M1' and 'M2' to the local namespace, we can check if both have the same direction (as specified in condition1):
            M1.get(('attribute', 'direction')) == M2.get(('attribute', 'direction'))
        or:    
            M1['attribute']['direction'] == M2['attribute']['direction']            
        '''
        for (name, message) in group: # for message_tuple in group ...
            locals()[name] = message # write messages to the local namespace so a condition can evaluate them
            #UGLY HACK: the contents of locals() should NOT be modified; changes may not affect the values of local and free variables used by the interpreter. http://docs.python.org/library/functions.html#locals

        try:
            ret = eval(condition)
        except AttributeError:
            ret = False
        return ret

    def __get_return(self, group):
        '''constructs a ConstituentSet returned by I{get_options}

        @type group: C{list} of C{tuple}'s of (C{str}, C{Message} or C{ConstituentSet})
        @param group: a list of message tuples of the form (message name, message) that will be combined into a constituent set.

        @rtype: C{ConstituentSet}
        @return: a C{ConstituentSet}, which combines a nucleus and aux. both can either be a C{Message} or C{ConstituentSet}
        '''
        message_dict = {}
        for (name, message) in group:
            message_dict[name] = message
        nucleus = message_dict[self.nucleus]
        aux = message_dict[self.aux]

        return ConstituentSet(relType = self.ruleType, nucleus=nucleus, aux=aux)

def exists(thing, namespace):
    '''checks if a variable/object/instance exists in the given namespace
    
    @type thing: C{str}
    @param thing: the name of a variable, objects, class instance etc.
    
    @type namespace: C{dict}
    @param namespace: a namespace (dictionary), e.g. locals() or globals()
    
    @rtype: C{bool}
    @return: True, if 'thing' exists in 'namespace'. Otherwise returns False.
    '''
    if namespace.has_key(thing):
        return True
    else:
        print "{0} is not in {1}".format(thing, namespace)
        return False


def read_messages(messages):
    '''
    Read messages from a string formatted according to the tab-deliniated format specified in the manual.

    @input messages: string representation of messages in format specified in manual
    @type messages: string
    @returns list of Message s
    '''
    ret = []    
    
    #messages = map(lambda x: x.strip('\n'),messages.split('\n\n'))
    messages_list = messages.strip('\n').split('\n\n') #divide string into individual messages
    #print len(messages)

    for m in messages_list:
        lines = m.split('\n')
        msgType = lines[0].strip()
        msg = Message(msgType)
        msg.update(parse_message_features(lines[1:],1))
        ret.append(msg)

    return ret


def parse_message_features(lines, tab):
    '''
    Recursive helper method for read_messages parses message features.

    @returns a C{nltk.featstruct.FeatDict} corresponding to the input string
    '''
    ret = nltk.featstruct.FeatDict()

    n = 0
    while n < len(lines):
        l = lines[n].split()

        if len(l) == 1: # if this is the beginning of a category, recusively call parse_message_features to create nested FeatDict

            end_of_feat = n + util.first_index(lines[n+1:], lambda x: util.lcount(x, '\t') <= tab)
            r = lines[n+1: end_of_feat+1] #find where this feature's specifying lines end

            #print r, n+1, end_of_feat

            ret[l[0]] = parse_message_features(r, tab+1) #recusively call parse_message_features
            n = end_of_feat #skip cursor to after nested featstruct

        elif len(l) == 2: #else if this is a regular value
            #print key, value
            ret[l[0]] = eval(l[1])

        else:
            raise Exception('MESSAGE READ ERROR')
        n += 1

    return ret

def read_rules(rules):
    '''
    Read rules from a string formatted according to the tab-deliniated format specified in the manual.

    @input rules: string representation of rules in format specified in manual
    @type rules: string
    @returns list of Rule s
    '''
    ret = []
    
    #rules = map(lambda x: x.strip('\n'),rules.split('\n\n'))
    rules_list = rules.strip('\n').split('\n\n')
    
    for rule in rules_list:
        rule = rule.split('\n')
        firstLineRegex = '(\w+)\((.+?) *(\w+), *(.+?) *(\w+)\)'
        match = re.findall(firstLineRegex, rule[0])
        if len(match) == 1:
            (name, input1type, input1name, input2type, input2name) = match[0]

            #print input1type
            #print input2type

            input1s = map(eval, input1type.split('|'))            
            input2s = map(eval, input2type.split('|'))

            inputs = util.index_sets([input1s,input2s])
        else:
            raise Exception('ERROR')

        for line in rule[1:]:
            line = line.strip()
            lineregex = re.compile('\((.*)\) *: *ConstituentSet\((.+) *, *(\w+), *(\w+)\) *: *(.+) *')
            match = re.findall(lineregex, line)
            if match:
                (condition, relType, nucleus, aux, heuristic) = match[0]
                #print condition
                condition = [__replace_names(condition, [input1name, input2name])]
                heuristic = __replace_names(heuristic, [input1name, input2name])
                if '' in condition: condition.remove('') #UGLY HACK
            else:
                #print line
                raise Exception('blah')

            for i in inputs:
                i1 = i[0]
                i2 = i[1]
                inputs = [(input1name, i1), (input2name, i2)]
                ret.append(Rule(relType, inputs, condition, nucleus, aux, int(heuristic)))

    return ret

def __replace_names(string, names):
    '''
    Helper method for read_rules replaces dot-indexed references to message values in string representation of rules into the get() statements required for Message s
    '''
    
    for n in names:

        matches = re.findall('(%s(?:(?:\.\w+)*))'%(n), string)
        for m in matches:
            r = m.split('.')
            r = r[0]+'.get('+str(tuple(r[1:]))+')'
            string = string.replace(m,r)
    return string

def bottom_up_plan(messages, rules, dtype = None, text= None):
    '''
    The main method implementing the Bottom-Up document structuring algorithm from "Building Natural Language Generation Systems" figure 4.17, p. 108.

    The method takes a list of C{Message}s and a set of C{Rule}s and creates a document plan by repeatedly applying the highest-scoring Rule-application (according to the Rule's heuristic score) until a full tree is created. This is returned as a C{DocPlan} with the tree set as I{children}.

    If no plan is reached using bottom-up, I{None} is returned.

    @param messages: a list of C{Message}s which have been selected during content selection for inclusion in the DocPlan
    @type messages: list of C{Message}s
    
    @param rules: a list of C{Rule}s specifying relationships which can hold between the messages
    @type rules: list of C{Rule}s
    
    @param dtype: an optional type for the document
    @type dtype: string
    
    @param text: an optional text string describing the document
    @type text: string
    
    @return: a document plan. if no plan could be created: return None
    @rtype: C{DocPlan} or C{NoneType}
    '''
    for message in messages:
        message.freeze() # make all messages (C{FeatDict}s) immutable
    constituent_sets = set(messages) # remove duplicate messages #TODO: change name!
    
    ret = __bottom_up_search(constituent_sets, rules)

    if ret: # if __bottom_up_search has found a valid plan ...
        children =  ret.pop() # pop returns an 'arbitrary' set element (there's only one)
        return DocPlan(dtype=dtype, text=text, children=children)
    else:
        return None

def __bottom_up_search(plans, rules):
    '''helper method for bottom_up_plan which performs recursive best-first-search

    @param plans: a set containing C{Message}s and/or C{ConstituentSet}s
    @type plans: C{set} of C{Message}s or C{ConstituentSet}s
    
    @param rules: a list of C{Rule}s specifying relationships which can hold between the messages
    @type rules: C{list} of C{Rule}s
        
    @return: a set containing one C{Message}, i.e. the first valid plan reached by best-first-search. returns None if no valid plan is found.
    @rtype: C{NoneType} or a C{set} of (C{Message}s or C{ConstituentSet}s)
    '''
    if len(plans) == 1:
        print "There's only one plan, so we'll use it:\n{0}\n".format(plans) #TODO: remove
        return plans
    elif len(plans) < 1:
        raise Exception('ERROR')
    else:
        #fitzgerald: options = map(lambda x: x.get_options(plans), rules)
        options = [rule.get_options(plans) for rule in rules]
        options = util.flatten(options)
        options_list = []
        for x, y, z in options:
            y.freeze()
            options_list.append( (x, y, z) )
            
        if options_list == []:
            print "There's no rule that can be applied to these plans:\n{0}\n".format(plans) #TODO:remove
            return None

        sorted_options = sorted(options_list, key = lambda (x,y,z): x, reverse=True) # sort all options by their score, beginning with the highest one
        for (score, new, removes) in sorted_options:
            '''
            new: a ConstituentSet that was generated by Rule.get_options()
            removes: a list containing those messages that are now part of 'new' and should therefore not be used again
            '''
            testSet = plans - set(removes)
            testSet = testSet.union(set([new])) # a set containing a ConstituentSet and one or more Messages that haven't been integrated into a structure yet
            ret = __bottom_up_search(testSet, rules)
            if ret:
                #print "When applying the rules to these plans:\n{1}\n, this is the result set:\n{2}\n".format(rules, testSet, ret) #TODO: remove 
                return ret
        #print "Sorry, none of the rules could be applied to any of these options:\n{1}\n".format(rules, sorted_options) #TODO:remove
        return None

