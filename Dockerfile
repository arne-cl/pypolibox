FROM nlpbox/nlpbox-base:16.04
MAINTAINER Arne Neumann <nlpbox.programming@arne.cl>

RUN apt-get update -y && apt-get upgrade -y && \
    apt-get install -y python-pip openjdk-8-jre python-lxml libyaml-dev

WORKDIR /opt

# install OpenCCG for surface realization, then install pypolibox
RUN wget https://downloads.sourceforge.net/project/openccg/openccg/openccg%20v0.9.5%20-%20deplen%2C%20kenlm%2C%20disjunctivizer/openccg-0.9.5.tgz && \
    tar -xvzf openccg-0.9.5.tgz && \
    git clone https://github.com/arne-cl/pypolibox.git

WORKDIR /opt/pypolibox
RUN python setup.py install

ENV PATH=/opt/openccg/bin:$PATH OPENCCG_HOME=/opt/openccg JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64

ENTRYPOINT ["pypolibox"]
