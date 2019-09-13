# Bounced Email Service

__Bounced Email Service__ separates incoming bounced emails in _temporary_
failures and _permanent_ failures (also called as _soft_ and _hard_ bounces) and
handles messages accordingly.

- The emails are forwarded from the HPI mailservers to the postfix mailserver on
  our services server (`openhpi-services.hpi.uni-potsdam.de`,
  `openhpi-services2.hpi.uni-potsdam.de`).
- The mailserver are configured to send the bounced emails to an amqp message
  queue.
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
  rabbitmq-server obsolete. If the __Bounced Email Service__ is installed on the
  postfix server, the postfix can send a bounced email directly to __Bounced
  Email Handler__. For this:
  - configure `/etc/postfix/main.cf` as shown above
  - add to `/etc/aliases` the `no-reply` user: `no-reply: | bouncedemails stdin`
  - assure, that the postfix user can execute `/usr/local/bin/bouncedemails`.
    This includes the write access to the sqlite3 database and the storage path
    (see config).

- __Bounced Email Service__ consumes the message queue. The message handler
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
directory.

The installation process is divided into two parts. By executing (as root) the
`install.sh` bash-script an optional rabbitmq-server will be installed as well
as the required python packages and the __Bounced Email Service__. In addition,
all rabbitmq prerequisites (vhost, user and queue) will be created for
test/development purposes.

If you don't need a local rabbitmq-server you can skip executing `install.sh`.
If so, execute as root `make install`. This will install only the necessary
python packages and the __Bounced Email Service__.

Before running the __Bounced Email Service__ you have to copy the
`bounced_email_service/config.template.yml` to
`bounced_email_service/config.yml` and adjust the values for production stage.

The python setup routine installs the packages and creates a link to
`/usr/local/bin/bouncedemails`. The installation process installs __Bounced
Email Service__ as a systemd service. Control the service with: `systemctl
status bouncedemails`. Adjust the the configuration in `config.yml` and start
the service with: `systemctl start bouncedemails`. The logging output is shown
by `journalctl -u bouncedemails`.

## Update

Change to the cloned repository and run `make update`. This pulls and apply new
changes. Adjust the the configuration in `config.yml` and start the service
with: `systemctl restart bouncedemails`.

## Environment (read this first)

__Bounced Email Service__ starts with `production` environment and disabled
`debug` mode by default. To start __Bounced Email Service__ in `develop` mode
you have to ensure that the systemd service is not running. Than run the service
with `/usr/local/bin/bouncedemails --env develop --debug run`

Ensure that __Bounced Email Service__ can connect to the xikolo-account service.
`ConnectionError`s are not catched and the services will stop immediately.
(Although `systemd` tries to restart the __Bounced Email Service__ after 3
seconds.)

## Development & Testing

This project can be developed and tested in a linux container. After installing the __Bounced Email Service__ as described above, stop the __Bounced Email Service__ (if running). Start a local webserver by `python3 develop_webserver.py 7001`. In another shell run the service in forground by `/usr/local/bin/bouncedemails --env develop --debug run`. In a 3rd shell send a testmail to rabbitmq-server by `cat tests/testmail |tests/send_mail_to_rabbitmq.sh`. This should give the output:
~~~
root@bouncedemails:~# /usr/local/bin/bouncedemails --env develop --debug run
bouncedemails - ------------- INCOMING MESSAGE -------------
bouncedemails - From:	MAILER-DAEMON@mail2de.some-provider.com (Mail Delivery System)
bouncedemails - Subject:	Undelivered Mail Returned to Sender
bouncedemails - To:	no-reply@mydomain.de
bouncedemails - Domain: mydomain.de
bouncedemails - Permanent: evil-address@some-provider.com
bouncedemails - Post request to: http://localhost:7001/emails/evil-address%40some-provider.com/suspend for address: evil-address@some-provider.com
bouncedemails - Response (200): {"processd_email": "evil-address@some-provider.com"} 
~~~
