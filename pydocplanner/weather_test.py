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
