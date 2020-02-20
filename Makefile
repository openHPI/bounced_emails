SHELL:=/bin/bash

.PHONY:
.SILENT:
.ONESHELL:

help:
	@echo
	@echo "  Welcome."
	@echo
	@echo "    Target            Description"
	@echo "    -------------------------------------------------------------------"
	@echo "    help              You're reading this"
	@echo "    clean             Cleanup installation"
	@echo "    checkout          To checkout files"
	@echo "    install           Clean, install set up project"
	@echo "    update            Clean, set up project"
	@echo "    serve             Restart service"
	@echo
	@echo "  Have fun!"
	@echo

_install_packages:
	apt update
	apt install -y rabbitmq-server amqp-tools make git python3 python3-dev python3-pip

_install_python:
	rm -f /usr/bin/python
	ln -s /usr/bin/python3 /usr/bin/python
	ln -s /usr/bin/pip3 /usr/bin/pip
	pip install pipenv

_update_repo:
	git pull origin master
	chown -R bouncedemails: .

_update_python:
	@if git diff --name-only HEAD~1 | grep 'Pipfile'; then \
		su --login bouncedemails -c 'pipenv install;'
	fi

_prepare_templates:
	cp bounced_email_service/config.template.yml bounced_email_service/config.yml
	cp ./resources/bouncedemails.template.service /etc/systemd/system/bouncedemails.service

_configure_rabbitmq:
	$(if $(RABBITMQ_USER),,$(error 'RABBITMQ_USER not set'))
	$(if $(RABBITMQ_PASSWD),,$(error 'RABBITMQ_PASSWD not set'))
	echo "Enable rabbitmq cli tools"
	rabbitmq-plugins enable rabbitmq_management
	echo "Set rabbitmq user, vhost and queue"
	rabbitmqctl add_vhost /bouncedemails
	rabbitmqctl add_user $(RABBITMQ_USER) $(RABBITMQ_PASSWD)
	rabbitmqctl set_permissions -p /bouncedemails $(RABBITMQ_USER) ".*" ".*" ".*"
	rabbitmqctl set_user_tags $(RABBITMQ_USER) administrator
	rabbitmqadmin declare queue --vhost=/bouncedemails name=bouncedemails durable=true -u $(RABBITMQ_USER) -p $(RABBITMQ_PASSWD)
	echo '[{rabbit, [{loopback_users, []}]}].' >> /etc/rabbitmq/rabbitmq.conf
	sed -i "s#{uservar}:{passvar}#$(RABBITMQ_USER):$(RABBITMQ_PASSWD)#" bounced_email_service/config.yml
	systemctl restart rabbitmq-server.service

_install_service:
	useradd --home-dir `pwd` --shell /bin/bash bouncedemails
	sed -i "s#{bounced_emails_path}#`pwd`#g" bounced_email_service/config.yml
	sed -i "s#{bounced_emails_path}#`pwd`#g" /etc/systemd/system/bouncedemails.service
	chown -R bouncedemails: .
	su --login bouncedemails -c 'pipenv install;'
	systemctl daemon-reload
	systemctl enable bouncedemails

_pyclean:
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf ./*.egg
	rm -rf ./*.egg-info

clean: _pyclean

checkout:
	@if [ -d .git ]; then \
		echo "Checking out Bounced Email Service"; \
		git pull origin master; \
	fi

update: clean _update_repo _update_python

install: clean _install_packages _install_python _prepare_templates _configure_rabbitmq _install_service
	echo ""
	echo "Before you start, you have to configure the config.yml !!"
	echo "for run bounced emails service in as service"
	echo "systemctl start bouncedemails.service"

serve:
	sudo systemctl stop bouncedemails.service
	sudo systemctl start bouncedemails.service
