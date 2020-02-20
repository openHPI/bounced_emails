#!/usr/bin/env python
import json
from urllib.parse import unquote
from http.server import BaseHTTPRequestHandler, HTTPServer


class S(BaseHTTPRequestHandler):
    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()

    def do_GET(self):
        self._set_headers()
        self.wfile.write(bytes(json.dumps({
            'user_url': 'http://localhost:7001/users/{id}',
            'email_url': 'http://localhost:7001/emails/{id}',
            'email_suspensions_url': 'http://localhost:7001/emails/{address}/suspend',
        }), 'utf8'))

    def do_HEAD(self):
        self._set_headers()

    def do_POST(self):
        status = 200
        try:
            email = self.path.split('/')[2]
            msg = bytes(json.dumps(
                {'processd_email': unquote(email)}), 'utf-8')
        except Exception as e:
            status = 405
            msg = bytes(json.dumps(str(e)), 'utf-8')

        self._set_headers(status)
        self.wfile.write(msg)


def run(server_class=HTTPServer, handler_class=S, port=7001):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)

    print('Starting httpd...')
    httpd.serve_forever()


if __name__ == "__main__":
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()
