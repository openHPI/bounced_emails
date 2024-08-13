# Bounced Email Service

__Bounced Email Service__ separates incoming bounced emails in _temporary_
failures and _permanent_ failures (also called as _soft_ and _hard_ bounces) and
handles messages accordingly.

## How it works
The undeliverable emails (bounced emails) are forwarded from the HPI mailservers
(mail4 and mail5) to the bouncedemails virtual machine. The __Bounced Email Service__ runs a SMTP server on a high port (default:2525). Therefore the
 sending HPI mailservers have to be configured to this IP and port. However,
this requires that the HPI mailservers can reach the bouncedemails virtual
machine.

- __Bounced Email Service__ computes the incoming mails. The message handler
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
As prerequisite you have to have installed: `python3, python3-pip`.
Further you have to have installed `pipenv`.

### Service
- run `pipenv install`
- copy `bounced_email_service/config.template.yml` to
`bounced_email_service/config.yml` and adjust the values for production stage.

Install the systemd control files for __Bounced_Email_Service__. In the
`resources` folder are examples for the systemd files. Adjust the values and
install the services.

## Development & Testing
Run the service as bouncedemails user in forground by `pipenv run python3 bounced_email_service/service.py --env develop --debug run-smtpserver --port 2525`.
In another terminal run the webserver in tests folder: `python3 develop_webserver.py 7001`.  
In a 3rd terminal send a testmail to SMTP server by `python3 send_message_to_smtp.py`. 
This should give the output in service:
~~~
bouncedemails - ------------- INCOMING MESSAGE -------------
bouncedemails - From:      MAILER-DAEMON@mail2de.some-provider.com (Mail Delivery System)
bouncedemails - Subject:   Undelivered Mail Returned to Sender
bouncedemails - To:        no-reply@mydomain.de
bouncedemails - Domain:    mydomain.de
bouncedemails - Permanent: evil-address@some-provider.com
bouncedemails - Post to:   http://localhost:7001/emails/evil-address%40some-provider.com/suspend - evil-address@some-provider.com
bouncedemails - Response:  200, {"processd_email": "evil-address@some-provider.com"}
~~~
(The `send_message_to_smtp.py` script output differ, since it fetches from different logentries)