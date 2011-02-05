import re
from document_planner import *
import MyTree


#specification of the rules
rules = """
Conjunction(Message('AverageOpinionMessage') M1, Message('AverageOpinionMessage') M2)
    (M1.udf_parent == M2.udf_parent and M1.polarity == M2.polarity):ConstituentSet(Conjunction,M1,M2):(2,M1.numOpinions+M2.numOpinions)

Contrast(Message('AverageOpinionMessage') M1, Message('AverageOpinionMessage') M2)
    (M1.udf_parent == M2.udf_parent and M1.polarity != M2.polarity):ConstituentSet(Contrast,M1,M2):(3,M1.numOpinions+M2.numOpinions)

WeakExplanation(Message('AverageOpinionMessage') M1, Message('AverageOpinionMessage') M2)
    (M1.udf == M2.udf_parent and M1.polarity == M2.polarity):ConstituentSet(WeakExplanation,M1,M2):(5,0)

StrongExplanation(Message('AverageOpinionMessage') M1, ConstituentSet(relType = 'Conjunction', nucleus=Message('AverageOpinionMessage')) M2)
    (M1.udf == M2.nucleus.udf_parent and M1.polarity == M2.nucleus.polarity):ConstituentSet(StrongExplanation,M1,M2):(10:0)

Sequence(Message('AverageOpinionMessage')|ConstituentSet() M1, Message('AverageOpinionMessage')|ConstituentSet() M2)
    ():ConstituentSet(Sequence,M1,M2):(1,0)
"""


#get the scored from the corpus file
#returns a dict of cfs mapped to a list of scores
def get_scores(infile):
    ret = {}

    for l in infile:
        if l[:3] == '[t]':
            continue
        n = l[:l.find('#')]
        if n == '':
            continue
        n=n.split(',')

        for score in n:
            (cf, opinion) = re.findall('([\w ]+)\[([\+\-]\d)\]', score.strip())[0]
            ret.setdefault(cf, []).append(eval(opinion))

    return ret
    
#read the corpus file
def read_scorefile(infile):
    with open(infile, 'r') as f:
        return get_scores(f.readlines())

#merge the dict from get_scores with the hierarchy, so cfs are agregated into udfs
def merge_scores(scores, hierarchy):
    dic = {}
    
    for (key, vals) in scores.iteritems():
        udfs = hierarchy.find_in_buckets(key)
        for udf in udfs:
            dic.setdefault(udf, [])
            dic[udf] += vals

    dic.pop('Not Placed')
    return dic

#create messages from the merged udf scores
def create_messages(scores, hierarchy):
    msgs = []
    for (key, vals) in scores.iteritems():
        m = Message('AverageOpinionMessage')
        m['numOpinions'] = len(vals)
        m['udf'] = key
        try:
            m['udf_parent'] = hierarchy.get_parent(key)[0]
        except IndexError:
            m['udf_parent'] = None
        a = avg(vals)
        m['valence'] = abs(a)
        if a > 0:
            m['polarity'] = '+'
        else:
            m['polarity'] = '-'
        msgs.append(m)
    return msgs

#returns average value of numbers in list
def avg(ls):
    return sum(map(float, ls))/len(ls)

def main():
    global rules
    hier = MyTree.read_hierarchy('data/apex.gold')
    scores = read_scorefile('data/apex.in')
    merged = merge_scores(scores, hier)
    msgs = create_messages(merged, hier)
    rules = read_rules(rules)
    #rules = read_rules(rules)
    plan = bottom_up_plan(msgs, rules)
    print plan
    

if __name__ == '__main__':
    main()
