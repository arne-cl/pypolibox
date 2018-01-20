import os
import sys
from setuptools import setup, find_packages
import platform

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
NEWS = open(os.path.join(here, 'NEWS.rst')).read()

version = '1.0.2'

if platform.system() == 'Windows':
    install_requires = ["lxml", "nltk", "winpexpect", "pyaml"]
else:
    install_requires = ["lxml", "nltk", "pexpect", "pyaml", "sphinxcontrib-napoleon"]


def gen_data_files(src_dir):
    """
    generates a list of files contained in the given directory (and its
    subdirectories) in the format required by the ``package_data`` parameter
    of the ``setuptools.setup`` function.

    Parameters
    ----------
    src_dir : str
        (relative) path to the directory structure containing the files to
        be included in the package distribution

    Returns
    -------
    fpaths : list(str)
        a list of file paths
    """
    fpaths = []
    base = os.path.dirname(src_dir)
    for root, dir, files in os.walk(src_dir):
        if len(files) != 0:
            for f in files:
                fpaths.append(os.path.relpath(os.path.join(root, f), base))
    return fpaths


package_data_list = gen_data_files('src/pypolibox/data/*')
package_data_list.extend(gen_data_files('src/pypolibox/grammar/*'))
package_data_list.append('src/pypolibox/avm.sty')


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
    package_data = {'pypolibox': package_data_list},
    zip_safe=False,
    install_requires=install_requires,
    entry_points={
        'console_scripts':
            ['pypolibox=pypolibox.pypolibox:main',
             'hlds-converter=pypolibox.hlds:main']
    }
)
