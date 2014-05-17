.. This is your project NEWS file which will contain the release notes.
.. Example: http://www.python.org/download/releases/2.6/NEWS.txt
.. The content of this file, along with README.rst, will appear in your
.. project's PyPI page.

News
====

1.0.2 (2014-05-17)
------------------

*Release data: 17-May-2014*

* added Windows-specific requirements to setup.py (``winpexpect`` vs. ``pexpect``)
* README now covers installation prerequisites


1.0.1 (2014-05-13)
------------------

*Release date: 13-May-2014*

* installation via ``pip`` or ``python setup.py install`` now adds two programs
  to your path: ``pypolibox`` and ``hlds-converter``
* added new output formats (``--output-format`` parameter):
  textplan featstructs, HLDS XML
* documentation is now hosted at `readthedocs.org <http://pypolibox.readthedocs.org>`_
* converted documentation from epydoc to sphinx
* added make file, license file


1.0.0 (2014-30-04)
------------------

*Release date: 30-Apr-2014*

* pypolibox is now licensed under GPLv3
* OpenCCG grammar fragment (CC-BY-NC-SA 4.0 licensed) now shipped with code
* first release via PyPI
* got rid of configuration file
* fixed some errors in the documentation
