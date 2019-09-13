#!/bin/bash
apt update
apt -y upgrade

# install all needed packages
apt install -y python3 rabbitmq-server amqp-tools make git

# set python3 as default
rm -f /usr/bin/python
ln -s /usr/bin/python3 /usr/bin/python

# enable rabbitmq cli tools
rabbitmq-plugins enable rabbitmq_management

# set rabbitmq user, vhost and queue
rabbitmqctl add_vhost /bouncedemails
rabbitmqctl add_user mwiesner geheim
rabbitmqctl set_permissions -p /bouncedemails mwiesner ".*" ".*" ".*"
rabbitmqctl set_user_tags mwiesner administrator
rabbitmqadmin declare queue --vhost=/bouncedemails name=bouncedemails durable=true -u mwiesner -p geheim
echo '[{rabbit, [{loopback_users, []}]}].' >> /etc/rabbitmq/rabbitmq.conf
systemctl restart rabbitmq-server.service

# install bounced emails
make install
cp bounced_email_service/config.template.yml bounced_email_service/config.yml

echo 'Start develop webserver'
echo 'python3 develop_webserver.py 7001'
echo
echo 'finally run bounced emails service in forground'
echo '/usr/local/bin/bouncedemails --env develop --debug run'
echo
echo 'for run bounced emails service in as service'
echo 'systemctl start bouncedemails.service'