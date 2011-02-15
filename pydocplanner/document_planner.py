import string, re
import nltk
import util
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



class DocPlan(nltk.featstruct.FeatDict):
    """
    C{DocPlan} is the output of Document Planning. A DocPlan consistes of an optional title and text, and a child I{ConstituentSet}.
    """
    def __init__(self, dtype = 'DocPlan', text = None, children = None):
        self[nltk.featstruct.Feature('type',display='prefix')] = 'DPDocument'
        self['title'] = nltk.featstruct.FeatDict({'type': dtype, 'text':text})
        self['children'] = children

class ConstituentSet(nltk.featstruct.FeatDict):
    """"
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
        if relType: self[nltk.featstruct.Feature('relType',display='prefix')] = relType
        if nucleus: self[nltk.featstruct.Feature('nucleus',display='prefix')] = nucleus
        if aux: self[nltk.featstruct.Feature('aux',display='prefix')] = aux

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
        if msgType: self[nltk.featstruct.Feature('msgType',display='prefix')] = msgType

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
        @param heuristic: string which will be evaluated to provide the heuristic value used to rank potential ConstituentSets
        @type heuristic: string
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
        """
        This is the main method used for document planning. From the list of C{Messages}, I{get_options} selects all possible ways the Rule could be applied. The method returns a 3-tuple: (score, const_set, inputs) where:
            score - is the evaluated heuristic score for this application of the Rule
            const_set - is the new C{ConstituentSet} returned by the application of the Rule
            inputs - is the list of inputs (C{Message}s or C{ConstituentSets} used in this application of the rule

        The planner can then select one of these possible applications of the Rule to use.
        """
        #print self.ruleType

        name_list = [] # a list containing the inputs names in order
        type_groups = [] # a list where each index is a list of all the input Messages which are subsumed by the input proto-type 

        for (name, cond) in self.inputs:
            name_list.append(name)
            type_groups.append(filter(lambda x: cond.subsumes(x), messages)) # add all messages which are subsumed by the input proto-type

        #print 'TYPE GROUPS:', type_groups, '\n' #for debugging

        groups = util.index_sets(type_groups)                           #get all possible combinations of inputs
        groups = filter(lambda x: len(x) == len(set(x)), groups)        #remove groups which contain duplicates
        groups = map(lambda x: zip(name_list, x), groups)               #match names to messages
        groups = filter(lambda g: all(map(lambda cond: self.__name_eval(cond, g), self.conditions)), groups) #remove groups which do not satisfy conditions
        if [] in groups: groups.remove([])

        #print 'GROUPS:', groups, '\n' #for debugging

        if len(groups) > 0: 
            ret = map(lambda x: (self.__name_eval(self.heuristic, x), self.__get_return(x), map(lambda (y,z): z, x)), groups) #create 3-tuple
            return ret
        else:
            return []

    def __name_eval(self, string, group):
        '''
        Evaluate I{string} using the name-mappings provided by I{group}
        '''
        for (name, msg) in group:
            locals()[name] = msg
        try:
            #print group
            ret = eval(string)
        except AttributeError:
            ret = False
        return ret

    def __get_return(self, group):
        '''
        Construct the ConstituentSet returned by I{get_options}
        '''
        nucleus = self.__name_eval(self.nucleus, group)
        aux = self.__name_eval(self.aux, group)

        return ConstituentSet(relType = self.ruleType, nucleus=nucleus, aux=aux)

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
                ret.append(Rule(relType, inputs, condition, nucleus, aux, heuristic))

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
    The main method implementing the Bottom-Up document structuring algorithm from "Building Natural Language Generation Systems" figure 4.17, pg 108.

    The method takes a list of C{Message}s and a set of C{Rule}s and creates a document plan by repeatedly applying the highest-scoring Rule-application (according to the Rule's heuristic score) until a full tree is created. This is returned as a C{DocPlan} with the tree set as I{children}.

    If no plan is reached using bottom-up, I{None} is returned.

    @input messages: a list of C{Message}s which have been selected during content selection for inclusion in the DocPlan
    @type messages: list of Message
    @input rule: a list of C{Rule}s specifying relationships which can hold between the messages
    @type rule: list of Rule
    @input dtype: an optional type for the document
    @type dtype: string
    @input text: an optional text string describing the document
    @type text: string
    '''
    map(lambda x: x.freeze(),messages)

    ConstituentSets = set(messages)
  
    ret = __bottom_up_search(ConstituentSets, rules)

    if ret:
        children =  ret.pop()
        return DocPlan(dtype=dtype, text=text, children=children)
    else:
        return None

'''
Helper method for bottom_up_plan which performs recursive best-first-search

Returns the first valid plan reached by best-first-search.
Returns None if no valid plan is possible.
'''
def __bottom_up_search(plans, rules):
    if len(plans) == 1:
        return plans
    elif len(plans) < 1:
        raise Exception('ERROR')
    else:
        options = map(lambda x: x.get_options(plans), rules)
        options = util.flatten(options)
        map(lambda (x,y,z): (x,y.freeze(),z),options)

        if options == []:
            return None

        for (score, new, removes) in sorted(options, key = lambda (x,y,z): x, reverse=True):
            testSet = plans - set(removes)
            testSet |= set([new])
            ret = __bottom_up_search(testSet, rules)
            if ret: 
                return ret
        return None
       
