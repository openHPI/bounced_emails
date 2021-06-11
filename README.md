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
exec amqp-publish -u amqp://<rabbitmq-user>:<rabbitmq-password>@<rabbitmq-server>/bouncedemails -r "bouncedemails"
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

As prerequisite you have to have installed: `python3, python3-pip, rabbitmq-server`.
Further you have to have installed `pipenv`.

### Rabbitmq-Server
- Create a vhost `bouncedemails`
- Create a user (e.g. bouncedemails) with password, with all permissions to the new created vhost

### Service
- run `pipenv install`
- copy `bounced_email_service/config.template.yml` to
`bounced_email_service/config.yml` and adjust the values for production stage.
- fill the credentials in `bounced_email_service/config.yml`

Install systemd control file for __Bounced_Email_Service__. In `resources` folder is
an example for the systemd file. Adjust the values and install the service.


## Development & Testing

Start a local webserver by `python3 tests/develop_webserver.py 7001`. In another shell run the service 
as bouncedemails user in forground by `pipenv run python3 bounced_email_service/service.py --env develop --debug run`. 
In a 3rd shell send a testmail to rabbitmq-server by `cat tests/testmail | tests/send_mail_to_rabbitmq.sh`. 
This should give the output:

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
