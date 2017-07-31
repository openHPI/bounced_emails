# Bounced Email Handler

__Bounced Email Handler__ separates incoming bounced emails in _temporary_ failures and _permanent_ failures (also called as _soft_ and _hard_ bounces) and handles messages accordingly.

- The emails are forwarded from the HPI mailservers to the postfix mailserver on our services server (`openhpi-services.hpi.uni-potsdam.de`, `openhpi-services2.hpi.uni-potsdam.de`).
- The mailserver are configured to send the bounced emails to an amqp message queue, provided by our openHPI rabbitmq-server.
- __Bounced Email Handler__ consumes the message queue. The message handler separates the incoming bounced email and handles them accordingly:
	- _Temporary_ failure: The accused email address in the bounced email and the domain from which the originally email was sent are stored in a local database together with a counter. The counter is incremented with each new incoming occurence. Once the counter exceeds a configured threshold, the accordingly email address is treaten as a permanent failure (and the counter is resetted).
	- _Permanent_ failure: The accused email address in the bounced email is reported to the xikolo-account service. The xikolo-account service disables all notifications regarding this email address.

## Install

`git clone` this repository to a modern ubuntu or debian. Change to the new directory and run as `root`: `make install`. This will install all necessary packages.
- The python setup routine installs the packages locally (the clone path) and creates a link to `/usr/local/bin/bouncedemails`
- The installation process installs __Bounced Email Handler__ as a systemd service. Control the service with: `systemctl status bouncedemails`
- Adjust the the configuration in `config.yml` and start the service with: `systemctl start bouncedemails`

## Update
Change to the cloned repository and run `make update`. This pulls and apply new changes. Adjust the the configuration in `config.yml` and start the service with: `systemctl restart bouncedemails`.