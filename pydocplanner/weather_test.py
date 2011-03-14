from document_planner import *

#original author: Nicholas FitzGerald
#cf. "Open-Source Implementation of Document Structuring Algorithm for NLTK"

messages = """
TotalRainfallMsg
	period
		year 1996
		month 06
	attribute
		type 'RelativeVariation'
		magnitude
			unit 'inches'
			number 4
		direction '+'

MonthlyRainfallMsg
	period
		year 1996
		month 06
	attribute
		type 'RelativeVariation'
		magnitude
			unit 'inches'
			number 2
		direction '+'

MonthlyTemperatureMsg
	period
		year 1996
		month 06
	temperature
		category 'hot'
"""
ruleset = """
Elaboration(Message('MonthlyRainfallMsg') M1, Message('TotalRainfallMsg') M2)
	(M1.attribute.direction == M2.attribute.direction) : ConstituentSet('Elaboration', M1, M2) : 3

Contrast(Message('MonthlyRainfallMsg') M1, Message('TotalRainfallMsg') M2)
	(M1.attribute.direction != M2.attribute.direction) : ConstituentSet('Contrast', M1, M2) : 2

Sequence(Message('MonthlyTemperatureMsg')|ConstituentSet(nucleus=Message('MonthlyTemperatureMsg')) M1, Message('MonthlyRainfallMsg')|ConstituentSet(nucleus=Message('MonthlyRainfallMsg')) M2)
	() : ConstituentSet(Sequence, M1, M2) : 1
"""



m = read_messages(messages)
r = read_rules(ruleset)
print bottom_up_plan(m,r)

'''
detailed run of the weather_test example:
=========================================

>>> from document_planner import __bottom_up_search
>>> for message in m: # 'replacing' bottom_up_plan
	message.freeze()
>>> const_sets = set(m)

>>> __bottom_up_search(const_sets, r)
set([Sequence[*aux*='Elaboration'[*aux*=TotalRainfallMsg[attribute=[direction='+', magnitude=[number=4, unit='inches'], type='RelativeVariation'], period=[month=6, year=1996]], *nucleus*=MonthlyRainfallMsg[attribute=[direction='+', magnitude=[number=2, unit='inches'], type='RelativeVariation'], period=[month=6, year=1996]]], *nucleus*=MonthlyTemperatureMsg[period=[month=6, year=1996], temperature=[category='hot']]]])
>>> ret = __bottom_up_search(const_sets, r)
>>> children = ret.pop()

>>> children
Sequence[*aux*='Elaboration'[*aux*=TotalRainfallMsg[attribute=[direction='+', magnitude=[number=4, unit='inches'], type='RelativeVariation'], period=[month=6, year=1996]], *nucleus*=MonthlyRainfallMsg[attribute=[direction='+', magnitude=[number=2, unit='inches'], type='RelativeVariation'], period=[month=6, year=1996]]], *nucleus*=MonthlyTemperatureMsg[period=[month=6, year=1996], temperature=[category='hot']]]

>>> DocPlan(children=children)
DPDocument[children=Sequence[*aux*='Elaboration'[*aux*=TotalRainfallMsg[attribute=[direction='+', magnitude=[number=4, unit='inches'], type='RelativeVariation'], period=[month=6, year=1996]], *nucleus*=MonthlyRainfallMsg[attribute=[direction='+', magnitude=[number=2, unit='inches'], type='RelativeVariation'], period=[month=6, year=1996]]], *nucleus*=MonthlyTemperatureMsg[period=[month=6, year=1996], temperature=[category='hot']]], title=[text=None, type='DocPlan']]

DocPlan: Sequence(nucleus=MonthlyTemp, aux=ConstituentSet)
    where aux=ConstituentSet consists of:
            Elaboration(nucleus=MonthlyRainfall, aux=TotalRainfall)

STEP BY STEP run of every iteration of >>> __bottom_up_search(plans, rules):

len(const_sets) = 3 -->

>>> options = [rule.get_options(const_sets) for rule in r]
>>> options = util.flatten(options)


options != [] --->

>>> for x,y,z in options: y.freeze()
>>> options = [(x,y,z) for (x,y,z) in options]
>>> print options
[(3, 'Elaboration'[*aux*=TotalRainfallMsg[attribute=[direction='+', magnitude=[number=4, unit='inches'], type='RelativeVariation'], period=[month=6, year=1996]], *nucleus*=MonthlyRainfallMsg[attribute=[direction='+', magnitude=[number=2, unit='inches'], type='RelativeVariation'], period=[month=6, year=1996]]], [MonthlyRainfallMsg[attribute=[direction='+', magnitude=[number=2, unit='inches'], type='RelativeVariation'], period=[month=6, year=1996]], TotalRainfallMsg[attribute=[direction='+', magnitude=[number=4, unit='inches'], type='RelativeVariation'], period=[month=6, year=1996]]]), (1, Sequence[*aux*=MonthlyRainfallMsg[attribute=[direction='+', magnitude=[number=2, unit='inches'], type='RelativeVariation'], period=[month=6, year=1996]], *nucleus*=MonthlyTemperatureMsg[period=[month=6, year=1996], temperature=[category='hot']]], [MonthlyTemperatureMsg[period=[month=6, year=1996], temperature=[category='hot']], MonthlyRainfallMsg[attribute=[direction='+', magnitude=[number=2, unit='inches'], type='RelativeVariation'], period=[month=6, year=1996]]])]

>>> sorted_options = sorted(options, key = lambda (x,y,z): x, reverse=True)

len(sorted_options) = 2 (#1: score = 3, #2: score = 1) -->

>>> o1, o2 = sorted_options
>>> o1
(3, 'Elaboration'[*aux*=TotalRainfallMsg[attribute=[direction='+', magnitude=[number=4, unit='inches'], type='RelativeVariation'], period=[month=6, year=1996]], *nucleus*=MonthlyRainfallMsg[attribute=[direction='+', magnitude=[number=2, unit='inches'], type='RelativeVariation'], period=[month=6, year=1996]]], [MonthlyRainfallMsg[attribute=[direction='+', magnitude=[number=2, unit='inches'], type='RelativeVariation'], period=[month=6, year=1996]], TotalRainfallMsg[attribute=[direction='+', magnitude=[number=4, unit='inches'], type='RelativeVariation'], period=[month=6, year=1996]]])

>>> score, new, removes = o1
>>> score
3
>>> new
'Elaboration'[*aux*=TotalRainfallMsg[attribute=[direction='+', magnitude=[number=4, unit='inches'], type='RelativeVariation'], period=[month=6, year=1996]], *nucleus*=MonthlyRainfallMsg[attribute=[direction='+', magnitude=[number=2, unit='inches'], type='RelativeVariation'], period=[month=6, year=1996]]]
>>> removes
[MonthlyRainfallMsg[attribute=[direction='+', magnitude=[number=2, unit='inches'], type='RelativeVariation'], period=[month=6, year=1996]], TotalRainfallMsg[attribute=[direction='+', magnitude=[number=4, unit='inches'], type='RelativeVariation'], period=[month=6, year=1996]]]

option 1: Elaboration(nucleus=MonthlyRainfall + aux=TotalRainfall) - score 3

>>> testset = const_sets - set(removes)
>>> testset
set([MonthlyTemperatureMsg[period=[month=6, year=1996], temperature=[category='hot']]])

only one message (MonthlyTemp) left to be combined w/ our Elaboration ConstituentSet ...

>>> testset = testset.union(set([new]))
set([MonthlyTemperatureMsg[period=[month=6, year=1996], temperature=[category='hot']], 'Elaboration'[*aux*=TotalRainfallMsg[attribute=[direction='+', magnitude=[number=4, unit='inches'], type='RelativeVariation'], period=[month=6, year=1996]], *nucleus*=MonthlyRainfallMsg[attribute=[direction='+', magnitude=[number=2, unit='inches'], type='RelativeVariation'], period=[month=6, year=1996]]]])

let's check if __bottom_up_search(testset, rules) returns anything. if so: return this, otherwise repeat the "score, new, removes etc." steps with all other options. if none of them returns anything, return none.

len(testset) = 2 -->

>>> __bottom_up_search(testset, r)
set([Sequence[*aux*='Elaboration'[*aux*=TotalRainfallMsg[attribute=[direction='+', magnitude=[number=4, unit='inches'], type='RelativeVariation'], period=[month=6, year=1996]], *nucleus*=MonthlyRainfallMsg[attribute=[direction='+', magnitude=[number=2, unit='inches'], type='RelativeVariation'], period=[month=6, year=1996]]], *nucleus*=MonthlyTemperatureMsg[period=[month=6, year=1996], temperature=[category='hot']]]])
>>> ret = __bottom_up_search(testset2, r)
>>> children = ret.pop()
>>> DocPlan(children=children)
DPDocument[children=Sequence[*aux*='Elaboration'[*aux*=TotalRainfallMsg[attribute=[direction='+', magnitude=[number=4, unit='inches'], type='RelativeVariation'], period=[month=6, year=1996]], *nucleus*=MonthlyRainfallMsg[attribute=[direction='+', magnitude=[number=2, unit='inches'], type='RelativeVariation'], period=[month=6, year=1996]]], *nucleus*=MonthlyTemperatureMsg[period=[month=6, year=1996], temperature=[category='hot']]], title=[text=None, type='DocPlan']]

since __bottom_up_search(testset, r) has a return value, it will be returned by __bottom_up_search(const_sets, r) also. we don't need to look at option 2...

option 2: Sequence(nucleus=MonthlyTemp + aux=MonthlyRainfall) - score 1
'''
