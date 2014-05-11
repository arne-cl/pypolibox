# a '-' before a shell command causes make to ignore its exit code (errors)

all:
	pypolibox -l English --xml

gitstats:
	git_stats generate --silent --output=/tmp/polibox
	firefox /tmp/polibox/lines/by_date.html

install:
	python setup.py install

uninstall:
	yes | pip uninstall pypolibox

clean:
	find . -name *.pyc -delete
	rm -rf git_stats /tmp/polibox
	rm -rf build dist pypolibox.egg-info
