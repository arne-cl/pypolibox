To-do list
----------

- **Theory/Structure**: Rewrite rules for the textplanner. RST relations should
  combine messages, not message blocks. (A message should be something that
  can be expressed in a single sentence.)
- **Coverage**: Update the lexicalization module once the grammar
  fragment is "completed".
- **Consistency**: Make keys unique. Instead of three different "recency" keys,
  there should be a regular one, an "extra_recency" key ('This book is
  particularly recent/old') and a "relative_recency" key ('This book is 20
  years older than the other one').
- **Consistency**: In "extra recency" messages, "values" are called
  "descriptions".
- **Unicode**: If NLTK becomes available for Python 3, switch to that branch.
  Otherwise, evaluate if porting nltk.featstruct to Python 3 is feasible
  (e.g. with the help of python2to3).
