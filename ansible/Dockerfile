# ================================================================================
# Provides a modern Ansible installation and 'ansible-playbook' entrypoint.
# Mount playbooks at:        /usr/src/playbooks
# Mount SSH private keys at: /.ssh
# ================================================================================

FROM centos:7
MAINTAINER Quintin May <quintin.may@hpe.com>

# ================================================================================
# Define proxies
# ================================================================================

ENV http_proxy="http://web-proxy.corp.hpecorp.net:8080" \
    https_proxy="http://web-proxy.corp.hpecorp.net:8080" \
    no_proxy="localhost,.hpe.com,.hpecorp.net,.hp.com,127.0.0.1,::1"

# ================================================================================
# Install CA certificates
# ================================================================================

COPY ca-certificates /etc/pki/ca-trust/source/anchors/
RUN update-ca-trust extract

# ================================================================================
# Install Ansible dependencies
# ================================================================================

RUN yum --assumeyes groupinstall "Development tools" \
 && yum install --assumeyes python-setuptools python2-devel libffi-devel openssl-devel bind-utils \
 && easy_install pip pycrypto \
 && pip install --upgrade paramiko PyYAML Jinja2 httplib2 six shade \
        python-openstackclient \
        dnspython

# ================================================================================
# Install Ansible
# ================================================================================

RUN cd /usr/local \
 && git clone https://github.com/ansible/ansible.git --recursive \
 && cd ansible \
 && git checkout v2.1.1.0-1 \
 && git submodule update --init --recursive \
 && . ./hacking/env-setup \
 && ansible-galaxy install peru.proxy_settings

ENV ANSIBLE_HOME=/usr/local/ansible
ENV PATH=$ANSIBLE_HOME/bin:$PATH \
    PYTHONPATH=$ANSIBLE_HOME/lib

# hack: https://github.com/ansible/ansible-modules-extras/issues/1414#issuecomment-166560718
# http://docs.python-requests.org/en/latest/user/advanced/
# required for Ansible module: os_object
ENV REQUESTS_CA_BUNDLE=/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem

# ================================================================================
# Prepare the ansbile-playbook interface
# ================================================================================

RUN mkdir /.ssh /usr/src/playbooks \
 && chmod u=rwx,go= /.ssh

WORKDIR /usr/src/playbooks
ENTRYPOINT ["ansible-playbook"]
