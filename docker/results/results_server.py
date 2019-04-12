#!/usr/bin/env python3

from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from sqltools import *
from threading import Thread
from time import time
from rate_limit import RateLimiter, Bucket, Period as Per
from collections import defaultdict
import json
import os
import re
import ssl

DB_URI = os.environ.get('DB_URI', 'sqlite:///clic2019.db')
HTTP_PORT = int(os.environ.get('RESULTS_HTTP_PORT', 80))
HTTPS_PORT = int(os.environ.get('RESULTS_HTTPS_PORT', 443))
RATE_LIMIT_SECOND = int(os.environ.get('RATE_LIMIT_SECOND', 3))
RATE_LIMIT_MINUTE = int(os.environ.get('RATE_LIMIT_SECOND', 20))


def create_rate_limiter():
	rate_of = Bucket.builder()
	limiter = RateLimiter(
		per_second=rate_of(RATE_LIMIT_SECOND, Per.SECOND),
		per_minute=rate_of(RATE_LIMIT_MINUTE, Per.MINUTE))
	return limiter


# creates and stores a rate limiter per IP
RATE_LIMITERS = defaultdict(create_rate_limiter)


class SimpleServer(ThreadingMixIn, HTTPServer):
	pass


class Handler(BaseHTTPRequestHandler):
	def _set_headers(self):
		self.send_response(200)
		self.send_header('Content-type', 'text/plain')
		self.end_headers()


	def do_GET(self):
		if not RATE_LIMITERS[self.client_address[0]].reduce():
			# too many requests
			self.send_error(429)

		else:
			match = re.match('/(?P<task>transparent|lowrate)/(?P<phase>test|valid)/?', self.path)

			if match is None:
				self.send_error(404)
			else:
				phase = match.group('phase')
				task = match.group('task')

				print('Connecting...')
				db = db_connect()

				print('Fetching results...')
				results = db_get_results(db, task, phase)

				print('Sending headers...')
				self._set_headers()

				print('Sending content...')
				self.wfile.write(b'window.leaderboard = ')
				self.wfile.write(json.dumps(results).encode())

				print('Closing connection...')
				db.close()
				print('Done.')

	def do_HEAD(self):
		self._set_headers()


def launch_server(https=False, port=80):
	httpd = SimpleServer(('', port), Handler)

	if https:
		httpd.socket = ssl.wrap_socket(
			httpd.socket,
			keyfile='./key.pem',
			certfile='./cert.pem',
			server_side=True)

	httpd.serve_forever()


if __name__ == "__main__":
	db_setup(DB_URI)

	http = Thread(target=launch_server, args=(False, HTTP_PORT))
	https = Thread(target=launch_server, args=(True, HTTPS_PORT))

	http.start()
	https.start()

	http.join()
	https.join()
