# InstaVPN

Interactive command-line tool to create EC2-based VPN connection between VPC.

## Requirements

* `Vagrant` plugins
	* [vagrant-librarian-chef](https://github.com/jimmycuadra/vagrant-librarian-chef):
	`vagrant plugin install vagrant-librarian-chef`

## License

Apache 2.0

## Directories

* `chef/`
* `doc/`
	Documents
* `src/`
    * `conf/`
    Most of them are system config files and should never be changed. Except for
    `instavpn.json`, which defines the default behavior of the suite.
    * `lib/`
    Libraries
    * `mock/`
    Mockup data used primarily for unit tests.
    * `instavpn.py`
	The main executable.

* `test/`

## Notice

Checks may be incomplete.
