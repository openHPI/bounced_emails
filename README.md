# Bounced Email Handler

__Bounced Email Handler__ separates incoming bounced emails in _temporary_
failures and _permanent_ failures (also called as _soft_ and _hard_ bounces) and
handles messages accordingly.

- The emails are forwarded from the HPI mailservers to the postfix mailserver on
  our services server (`openhpi-services.hpi.uni-potsdam.de`,
  `openhpi-services2.hpi.uni-potsdam.de`).
- The mailserver are configured to send the bounced emails to an amqp message
  queue, provided by our openHPI rabbitmq-server.
  - add the domains which should be handled to `/etc/postfix/main.cf` to
      `mydestination = ..., openhpi.de, opensap.info`:
  - add to `/etc/aliases` the `no-reply` user: `no-reply:
      |/usr/local/bin/send_message_to_rabbitmq.sh`
  - create the file `/usr/local/bin/send_message_to_rabbitmq.sh` with:

```bash
#!/bin/bash
exec amqp-publish -u amqp://<rabbitmq-user>:<rabbitmq-password>@<rabbitmq-server>/%2fbouncedemails -r "bouncedemails"
```

- _Update_: Read Email body from `stdin`:
  Alternatively the email can be read from the standard input. This makes the
  rabbitmq-server obsolete. If the __Bounced Email Handler__ is installed on the
  postfix server, the postfix can send a bounced email directly to __Bounced
  Email Handler__. For this:
  - configure `/etc/postfix/main.cf` as shown above
  - add to `/etc/aliases` the `no-reply` user: `no-reply: | bouncedemails stdin`
  - assure, that the postfix user can execute `/usr/local/bin/bouncedemails`.
    This includes the write access to the sqlite3 database and the storage path
    (see config).

- __Bounced Email Handler__ consumes the message queue. The message handler
  separates the incoming bounced email and handles them accordingly:
  - _Temporary_ failure: The accused email address in the bounced email and the
    domain from which the originally email was sent are stored in a local
    database together with a counter. The counter is incremented with each new
    incoming occurence. Once the counter exceeds a configured threshold, the
    accordingly email address is treaten as a permanent failure (and the counter
    is resetted).
  - _Permanent_ failure: The accused email address in the bounced email is
    reported to the xikolo-account service. The xikolo-account service disables
    all notifications regarding this email address.

## Install

As prerequisite you have to have installed: `git` and `make`.

`git clone` this repository to a modern ubuntu or debian. Change to the new
directory and run as `root`: `make install`. This will install all necessary
packages.

- The python setup routine installs the packages locally (the clone path) and
  creates a link to `/usr/local/bin/bouncedemails`
- The installation process installs __Bounced Email Handler__ as a systemd
  service. Control the service with: `systemctl status bouncedemails`
- Adjust the the configuration in `config.yml` and start the service with:
  `systemctl start bouncedemails`

## Update

Change to the cloned repository and run `make update`. This pulls and apply new
changes. Adjust the the configuration in `config.yml` and start the service
with: `systemctl restart bouncedemails`.

## Environment (read this first)

__Bounced Email Handler__ starts with `production` environment and disabled
`debug` mode by default. To start __Bounced Email Handler__ in `develop` mode
you have to ensure that the systemd service is not running. Than run the service
with `/usr/local/bin/bouncedemails --env develop --debug run`

Ensure that __Bounced Email Handler__ can connect to the xikolo-account service.
`ConnectionError`s are not catched and the services will stop immediately.
(Although `systemd` tries to restart the __Bounced Email Handler__ after 3
seconds.)

## Development & Testing

This project can be developed and tested in a vagrant box. The vagrant command
`vagrant up` starts a virtual machine and provision __Bounced Email Handler__
within. At the end of the provision the __Bounced Email Handler__ service will
be started.  
With the `amqp-tools` you can publish email contents, f.e: `cat bounced_mail.txt
| amqp-publish -u amqp://mwiesner:geheim@192.168.2.1/%2fbouncedemails -r
bouncedemails`

If you need to develop or change the config, you have to stop the vagrant
console and the service (2 times `<CTRL>+C`) first, do the changes, enter the
the virtual machine `vagrant ssh` and start the __Bounced Email Handler__
service by: `/usr/local/bin/bouncedemails --env develop --debug run`.