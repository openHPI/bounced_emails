$script = <<SCRIPT
apt update
apt -y upgrade

# install all needed packages
apt install -y python3 rabbitmq-server amqp-tools make git nginx

# set python3 as default
rm -f /usr/bin/python
ln -s /usr/bin/python3 /usr/bin/python

# enable rabbitmq cli tools
rabbitmq-plugins enable rabbitmq_management
updatedb
rabbitmqadmin=$(locate rabbitmqadmin)
chmod +x $rabbitmqadmin

# set rabbitmq user, vhost and queue
rabbitmqctl add_vhost /bouncedemails
rabbitmqctl add_user mwiesner geheim
rabbitmqctl set_permissions -p /bouncedemails mwiesner ".*" ".*" ".*"
rabbitmqctl set_user_tags mwiesner administrator
$rabbitmqadmin declare queue --vhost=/bouncedemails name=bouncedemails durable=true -u mwiesner -p geheim

# install bounced emails
cd /vagrant
make install

# finally run bounced emails service
echo '/usr/local/bin/bouncedemails --env develop --debug run'
SCRIPT

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/xenial64"

  config.vm.define "servicehost" do |master|
    master.vm.network :private_network, ip: "192.168.2.1"
    master.vm.network "forwarded_port", guest: 15672, host: 15672
  end

  config.vm.provision "shell", inline: $script
end