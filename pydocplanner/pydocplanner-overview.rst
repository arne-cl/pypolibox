introduction
============

py_docplanner is a  textplanner implemented by nicholas fitzgerald followed the principles laid out in Reiter and Dale (2000). he is focussing on Reiter and Dale's WeatherReporter example. 

in the following section, i will document the files of the project and will briefly summarise their contents.

the code is licensed under a creative commons license. #TODO: check which one


doc
===

contains an auto-generated epydoc documentation and:

cs503_project_report.pdf
------------------------

- 9 pages document describing the project and its implementation




code
====

contains the source code and a README file.


assess_test.py (99LOC):
~~~~~~~~~~~~~~~~~~~~~~~

document_planner.py (326LOC):
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

py_docplanner does use a modified version of the Bottom-Up Document Structuring algorithm from Reiter and Dale (2000), using a 'best-first local search' to generate a bottom-up plan.

#TODO: compare these two algorithms (given in Fig. 1 and 5 in cs503_project_report.pdf)

MyTree.py (159LOC):
~~~~~~~~~~~~~~~~~~~

util.py (85LOC):
~~~~~~~~~~~~~~~

weather_test.py (46LOC):
~~~~~~~~~~~~~~~~~~~~~~~~
