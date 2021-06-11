#!/bin/bash
exec amqp-publish -u amqp://mwiesner:geheim@localhost/bouncedemails -r "bouncedemails"