import string, re
import nltk
import util
import itertools
from nltk.featstruct import Feature
#from pypolibox import Messages # TODO: move Messages to textplan.py

#original author: Nicholas FitzGerald
# major rewrite: Arne Neumann
#cf. "Fitzgerald, Nicholas (2009). Open-Source Implementation of Document Structuring Algorithm for NLTK"

class DocPlan(nltk.featstruct.FeatDict):
    """
    C{DocPlan} is the output of Document Planning. A DocPlan consists of an optional title and text, and a child I{ConstituentSet}.
    """
    def __init__(self, book_score = None, dtype = 'DocPlan', text = None, children = None):
        self[nltk.featstruct.Feature('type',display='prefix')] = 'DPDocument'
        self['title'] = nltk.featstruct.FeatDict({'type': dtype, 'text':text, 'book score': book_score})
        self['children'] = children

class ConstituentSet(nltk.featstruct.FeatDict):
    """
    C{ConstituentSet} is the contstuction built up by applying C{Rules} to a set of C{ConstituentSet}s and C{Message}s. Each C{ConstituentSet} is of a specific I{relType}, and has two constituents, one which is designated the I{nucleus} and one which is designated I{aux}. These C{ConstituentSet}s can then be combined with other C{ConstituentSet}s or C{Message}s.

    C{ConstituentSet} is based on C{nltk.featstruct.FeatDict}.
    """
    def __init__(self, relType = None, nucleus = None, satellite = None):
        """
        I{relType}, I{nucleus} and I{aux} are only specified for the C{nltk.featstruct.FeatDict} if they are specified by the user.

        @param relType: The relation type which related the I{nucleus} to I{aux}.
        @type relType: string
        @param nucleus: Nucleus constituent. C{Message} or C{ConstituentSet}.
        @type nucleus: Message or ConstituentSet
        @param satellite: Auxiliary constituent. C{Message} or C{ConstituentSet}.
        @type satellite: Message or ConstituentSet
        """
        if relType: 
            self[nltk.featstruct.Feature('relType',display='prefix')] = relType
        if nucleus: 
            self[nltk.featstruct.Feature('nucleus',display='prefix')] = nucleus
        if satellite: 
            self[nltk.featstruct.Feature('satellite',display='prefix')] = satellite

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
    '''
    C{Rules} are the elements which specify relationships which hold between elements of the document. These elements can be I{Message}s or I{ConstituentSet}s.

    Each I{Rule} specifies a list of I{inputs}, which are is a minimal specification of a C{Message} or C{ConstituentSet}. To be a valid input to this Rule, a given C{Message} or C{ConstituentSet} must subsume one of the specified I{input}s.

    Each I{Rule} can also specify a set of conditions which must be met in order for the Rule to hold between the inputs.

    Each I{Rule} specifies a heuristic, which will be evaluated to provide a score by which to rank the order in which rules should be applied.

    Each I{Rule} specifies which of the inputs will be the I{nucleus} and which will be the I{aux} of the output C{ConstituentSet}.
    '''

    def __init__(self, name, ruleType, nucleus, satellite, conditions, heuristic):
        '''
        @param name: The name of the rule.
        @type name: string
        
        @param ruleType: The name of the relationship type this Rule specifies.
        @type ruleTupe: string
            
        @param conditions: a list of strings which will be evaluated as conditions for applying the rule. These should return True or False when evaluated
        @type conditions: list of strings
      
        @param nucleus: A list of tuples containing (name, input). I{name} is a string specifying the name used for the nucleus message of the RST relation. The name is used to refer to this message in the I{conditions} and I{heuristic}. I{input} is a C{Message} or C{ConstituentSet}. There can be only one nucleus in a RST relation, so the planner has to choose from the list.
        @type nucleus: list of tuples: (string, C{Message} or C{ConstituentSet})
      
        @param satellite: same as I{nucleus}, but represents a list of possible satellite messages of a RST relation. Again, there can be only one satellite in a RST relation, so the planner has to choose from the list.
        
        @param heuristic: an integer used to rank potential ConstituentSets. 
        @type heuristic: C{int}
        '''
        self.name = name
        self.ruleType = ruleType
        self.conditions = conditions
        self.nucleus = nucleus
        self.satellite = satellite
        self.heuristic = heuristic

    def __str__(self):
        """
        This is just a simple string output for the rule which is mainly used for debugging.
        """
        ret = ''
        for (key, val) in self.__dict__.iteritems():
            ret += str(key) + ' - ' + str(val) + '\n'
        return ret

    def get_options(self, messages):
        """these main method used for document planning 
        
        From the list of C{Messages}, I{get_options} selects all possible ways the Rule could be applied.

        The planner can then select -- with the __bottom_up_search function -- one of these possible applications of the Rule to use.
        
        #non_empty_message_combinations: list of combinations, where each combination is a (nucleus, satellite)-tuple. both the nucleus and the satellite each consist of a (name, message) tuple. #TODO: merge w/ function description!

        @type messages: list of C{Message} objects
        @param messages: a list of C{Message} objects, each containing one message about a book
        
        @rtype: empty list or a list containing one C{tuple} of (C{int}, C{ConstituentSet}, C{list}), where C{list} consists of C{Message} or C{ConstituentSet} objects 
        @return: a list containing one 3-tuple (score, C{ConstituentSet}, inputs}) where:
            score - is the evaluated heuristic score for this application of the Rule
            const_set - is the new C{ConstituentSet} returned by the application of the Rule
            inputs - is the list of inputs (C{Message}s or C{ConstituentSets} used in this application of the rule
            returns an empty list if I{get_options} can't find a way to to apply the I{Rule}.
        """
        self.messages = messages # will be used by self.__name_eval()
        nucleus_candidates = []
        satellite_candidates = []

        for message_prototype in self.nucleus:
            nucleus_candidates.extend( self.find_message_candidates(messages, message_prototype) )

        for message_prototype in self.satellite:
            satellite_candidates.extend( self.find_message_candidates(messages, message_prototype) )
        
        possible_msg_combinations = list(itertools.product(nucleus_candidates, satellite_candidates)) #cartesian product (all possible combinations) of nucleus and satellite messages 
        
        condition_matching_combinations = self.get_satisfactory_groups(possible_msg_combinations) #remove messages which do not satisfy conditions
        
        non_empty_message_combinations = [msgs for msgs in condition_matching_combinations if msgs != [] ] # remove empty messages

        self.combinations = non_empty_message_combinations #TODO: remove after debugging
        
        #return nucleus_candidates, satellite_candidates, possible_msg_combinations, condition_matching_combinations, non_empty_message_combinations #TODO: remove
 
        options_list = []
        inputs = []
        for i, combination in enumerate(non_empty_message_combinations):
            score = self.heuristic
            constituent_set = self.__get_return(combination)
            (nucleus_name, nucleus_msg), (sat_name, sat_msg) = combination
            inputs.append(nucleus_msg)
            inputs.append(sat_msg)
            options_list.append( (score, constituent_set, inputs) )
        return options_list            

    def find_message_candidates(self, messages, message_prototype):
        """takes a list of messages and returns only those with the right message type (as specified in Rule.inputs)
        
        @type messages: C{list} of C{Message}s
        @param messages: a list of C{Message} objects, each containing one message about a book

        @param message_prototype: a tuple consisting of a message name and a C{Message} or C{ConstituentSet}
        @type message_prototype: C{tuple} of (string, C{Message} or C{ConstituentSet})

        @rtype: C{list} of C{tuple}s of (string, C{Message})
        @return: a list containing all (name, message) tuples which are subsumed by the input message type (self.nucleus or self.satellite) -- if a rule should only be applied to UserModelMatch and UserModelNoMatch messages, the return value contains a list of messages with these types. 
        """
        messages_list = []
        name, condition = message_prototype
        for message in messages:            
            if condition.subsumes(message):
                messages_list.append( (name, message) )
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
            try:
                results.append( self.__name_eval(condition, group) )
            except NameError:
                '''__name_eval can check for the existence of an object, but it will fail "do something" with a nonexisting object, e.g. "len(lastbook_match) < 5" would raise an error if lastbook_match doesn't exist'''
                results.append(False)
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
        for message in self.messages:
            if message.has_key(Feature("msgType")): #if it's a C{Message} and not a C{ConstituentSet}
                message_name = message[Feature("msgType")]
                locals()[message_name] = message

        try:
            ret = eval(condition)
        except AttributeError:
            ret = False
        return ret

    def __get_return(self, combination):
        '''constructs a ConstituentSet returned by I{get_options}

        @type combination: C{tuple} of two C{tuple}s of (C{str}, C{Message} or C{ConstituentSet})
        @param combination: a tuple of two message tuples -- the first one represents the nucleus, the second one the satellite -- of the form (message name, message) that will be combined into a constituent set.

        @rtype: C{ConstituentSet}
        @return: a C{ConstituentSet}, which combines a nucleus and aux. both can either be a C{Message} or C{ConstituentSet}
        '''
        (nucleus_name, nucleus_msg), (sat_name, sat_msg) = combination
        return ConstituentSet(relType = self.ruleType, nucleus=nucleus_msg, satellite=sat_msg)

def exists(thing, namespace):
    '''checks if a variable/object/instance exists in the given namespace
    
    @type thing: C{str}
    @type namespace: C{dict}
    @rtype: C{bool}
    '''
    if namespace.has_key(thing):
        return True
    else:
        return False


def generate_textplan(messages, rules, book_score = None, dtype = None, text = None):
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
    if isinstance(messages, list):
        for message in messages:
            message.freeze() # make all messages (C{FeatDict}s) immutable
        messages_set = set(messages) # remove duplicate messages
    elif isinstance(messages, Messages):
        book_score = messages.book_score
    ret = __bottom_up_search(messages_set, rules)

    if ret: # if __bottom_up_search has found a valid plan ...
        children =  ret.pop() # pop returns an 'arbitrary' set element (there's only one)
        return DocPlan(book_score=book_score, dtype=dtype, text=text, children=children)
    else:
        return None

def __bottom_up_search(messages, rules):
    '''helper method for generate_text which performs recursive best-first-search

    @param messages: a set containing C{Message}s and/or C{ConstituentSet}s
    @type messages: C{set} of C{Message}s or C{ConstituentSet}s
    
    @param rules: a list of C{Rule}s specifying relationships which can hold between the messages
    @type rules: C{list} of C{Rule}s
        
    @return: a set containing one C{Message}, i.e. the first valid plan reached by best-first-search. returns None if no valid plan is found.
    @rtype: C{NoneType} or a C{set} of (C{Message}s or C{ConstituentSet}s)
    '''
    if len(messages) == 1:
        return messages
    elif len(messages) < 1:
        raise Exception('ERROR')
    else:
        try:
            options = [rule.get_options(messages) for rule in rules]
        except:
            raise Exception('EPIC FAIL: Rule {0} had trouble with these messages: {1}'.format(rule, messages))
            print "BOO" #TODO: remove after debugging
            
        options = util.flatten(options)
        options_list = []
        for x, y, z in options:
            y.freeze()
            options_list.append( (x, y, z) )
            
        if options_list == []:
            return None

        sorted_options = sorted(options_list, key = lambda (x,y,z): x, reverse=True) # sort all options by their score, beginning with the highest one
        for (score, rst_relation, removes) in sorted_options:
            '''
            rst_relation: a ConstituentSet (RST relation) that was generated by Rule.get_options()
            removes: a list containing those messages that are now part of 'rst_relation' and should therefore not be used again
            '''
            testSet = messages - set(removes)
            testSet = testSet.union(set([rst_relation])) # a set containing a ConstituentSet and one or more Messages that haven't been integrated into a structure yet
            ret = __bottom_up_search(testSet, rules)
            if ret:
                return ret
        return None
