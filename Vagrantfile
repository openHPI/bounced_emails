Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/xenial64"

  config.vm.define "servicehost" do |master|
    master.vm.network :private_network, ip: "192.168.2.1"
    master.vm.network "forwarded_port", guest: 15672, host: 15672
  end
end