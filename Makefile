SHELL:=/bin/bash

help:
	@echo
	@echo "  Welcome."
	@echo
	@echo "    Target            Description"
	@echo "    -------------------------------------------------------------------"
	@echo "    clean             Cleanup installation"
	@echo "    help              You're reading this"
	@echo "    install           Clean, install set up project"
	@echo "    update            Clean, set up project"
	@echo
	@echo "  Have fun!"
	@echo

pyclean:
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf ./*.egg
	rm -rf ./*.egg-info

clean: pyclean

install_packages:
	apt update
	apt install -y python3 python3-setuptools python3-pip
	pip3 install pipenv

systemctl_install:
	cp ./resources/bouncedemails.service /lib/systemd/system/bouncedemails.service
	systemctl daemon-reload
	systemctl enable bouncedemails

install_project:
	pipenv install --system
	python3 ./setup.py develop

update: clean
	git pull origin master
	pipenv install
	python3 ./setup.py develop

install: clean install_packages install_project systemctl_install
