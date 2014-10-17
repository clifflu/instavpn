# -*- mode: ruby -*-
# vi: set ft=ruby :

VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

  config.vm.box = "ub_14.04"
  config.vm.box_url = "https://cloud-images.ubuntu.com/vagrant/trusty/current/trusty-server-cloudimg-amd64-vagrant-disk1.box"

  config.vm.synced_folder ".", "/vagrant", mount_options: ["dmode=550,fmode=440"]
  config.vm.synced_folder "src", "/srv/instavpn", mount_options: ["dmode=755,fmode=644"]

  config.vm.provider "virtualbox" do |vb|
    vb.customize ["modifyvm", :id, "--memory", "1024"]
  end

  config.librarian_chef.cheffile_dir = "chef" # vagrant-librarian-chef

  config.vm.provision :chef_solo do |chef|
    chef.cookbooks_path = "chef/cookbooks"
    chef.json = {}
    chef.add_recipe "python"
    chef.add_recipe "python::pip"
  end
end
