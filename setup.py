import os
import sys
from setuptools import setup, find_packages
import platform

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
NEWS = open(os.path.join(here, 'NEWS.rst')).read()

version = '1.0.2'

if platform.system() == 'Windows':
    install_requires = ["lxml", "nltk", "winpexpect"]
else:
    install_requires = ["lxml", "nltk", "pexpect", "sphinxcontrib-napoleon"]


setup(name='pypolibox',
    version=version,
    description="text generation for product recommendations using OpenCCG",
    long_description=README + '\n\n' + NEWS,
    # Get classifiers from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[c.strip() for c in """
        Development Status :: 4 - Beta
        License :: OSI Approved :: GNU General Public License v3 (GPLv3)
        Operating System :: OS Independent
        Programming Language :: Python :: 2.7
        Topic :: Text Processing :: Linguistic
    """.split('\n') if c.strip()],
    keywords='linguistics nlp nlg',
    author='Arne Neumann',
    author_email='pypolibox.programming@arne.cl',
    url='https://github.com/arne-cl/pypolibox',
    license='GPL Version 3',
    packages=['pypolibox'],
    package_dir = {'pypolibox': "src/pypolibox"},
    package_data = {'pypolibox': ['data/*', 'grammar/*', 'avm.sty']},
    zip_safe=False,
    install_requires=install_requires,
    entry_points={
        'console_scripts':
            ['pypolibox=pypolibox.pypolibox:main',
             'hlds-converter=pypolibox.hlds:main']
    }
)
