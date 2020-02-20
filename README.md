# Bounced Email Service

__Bounced Email Service__ separates incoming bounced emails in _temporary_
failures and _permanent_ failures (also called as _soft_ and _hard_ bounces) and
handles messages accordingly.

## How it works
- The undeliverable emails are forwarded from the HPI mailservers to the postfix
  mailserver on our router (`router-{a,b}.oob.xopic.de`).
- The mailserver is configured to send the bounced emails to an amqp message
  queue running on the __Bounced Email Service__.
  - add the domains which should be handled to `/etc/postfix/main.cf` to
      `mydestination = ..., openhpi.de, opensap.info`:
  - add to `/etc/aliases` the `no-reply` user: `no-reply:|/usr/local/bin/send_message_to_rabbitmq.sh`
  - create the file `/usr/local/bin/send_message_to_rabbitmq.sh` with:

```bash
#!/bin/bash
exec amqp-publish -u amqp://<rabbitmq-user>:<rabbitmq-password>@<rabbitmq-server>/%2fbouncedemails -r "bouncedemails"
```

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
  
### Handling permanent failures
If the __Bounced Email Service__ detects a permanent failure, then the
responsible plattform will be informed. The plattform is determined by the
`no-reply` address, e.g. `no-reply@openhpi.de`. The __Bounced Email Service__
tries to POST-request the plattform. The accordingly HTTP endpoint MUST be
defined in the `config.yml`. See `bounced_email_service/config.template.yml`.
The `base_url` endpoint MUST include `{address}` as an URL part. E.g.
"http://mydomain.de/emails/{address}/suspend"

## Install

As prerequisite you have to have installed: `git` and `make`.

Change to a proper directory. e.g. `/opt`. `git clone` this repository
and change to the new directory.

Set the rabbitmq credentials as environment variables:  
```bash
export RABBITMQ_USER=xyz
export RABBITMQ_PASSWD=abc
```
These credentials will be used to configure rabbitmq-server and write the
`bounced_email_service/config.template.yml` during the install process.
Type as root `make install`. This will install all necessary packages, configure
rabbitmq-server, install and configure the service and all dependencies. During
the install process an user will be created with this curren directory as home
directory. The python dependencies will be installed by pipenv in a user's local
virtualenv.

Before running the __Bounced Email Service__ you have to copy the
`bounced_email_service/config.template.yml` to
`bounced_email_service/config.yml` and adjust the values for production stage.

The install routine installs systemd control files for __Bounced_Email_Service__. 
Control the service with: `systemctl status bouncedemails`. Adjust the the
configuration in `config.yml` and start the service with: `systemctl start
bouncedemails`. The logging output is shown by `journalctl -u bouncedemails`.

## Update

Change to the cloned repository and run `make update`. This pulls and apply new
changes. Adjust the the configuration in `config.yml` if needed and restart the
service with: `make serve`.

## Environment (read this first)

__Bounced Email Service__ starts with `production` environment and disabled
`debug` mode by default. To start __Bounced Email Service__ in `develop` mode
you have to ensure that the systemd service is not running. To start the service
in debug mode, run as `bouncedemails` user in the base directory `pipenv run python3 bounced_email_service/service.py --debug --env develop run`

Ensure that __Bounced Email Service__ can connect to the xikolo-account service.
`ConnectionError`s are not catched and the services will stop immediately.
(Although `systemd` tries to restart the __Bounced Email Service__ after 3
seconds.)

## Development & Testing

This project can be developed and tested in a linux container. After installing the __Bounced Email Service__ as described above, stop the __Bounced Email Service__ (if running). Start a local webserver by `python3 tests/develop_webserver.py 7001`. In another shell run the service as bouncedemails user in forground by `pipenv run python3 bounced_email_service/service.py --env develop --debug run`. In a 3rd shell send a testmail to rabbitmq-server by `cat tests/testmail | tests/send_mail_to_rabbitmq.sh`. This should give the output:
~~~
root@bouncedemails:~# journalctl -f -u bouncedemails.service
bouncedemails - ------------- INCOMING MESSAGE -------------
bouncedemails - From:      MAILER-DAEMON@mail2de.some-provider.com (Mail Delivery System)
bouncedemails - Subject:   Undelivered Mail Returned to Sender
bouncedemails - To:        no-reply@mydomain.de
bouncedemails - Domain:    mydomain.de
bouncedemails - Permanent: evil-address@some-provider.com
bouncedemails - Response:  200 / {"processd_email": "evil-address@some-provider.com"}
~~~
