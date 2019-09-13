#!/bin/bash
exec amqp-publish -u amqp://mwiesner:geheim@localhost/%2fbouncedemails -r "bouncedemails"