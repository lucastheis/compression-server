#!/usr/bin/env python3

from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from sqltools import *
import json
import os
import re

DB_URI = os.environ.get('DB_URI', 'sqlite:///clic2019.db')
PORT = os.environ.get('RESULTS_PORT', 8000)


class SimpleServer(ThreadingMixIn, HTTPServer):
	pass


class Handler(BaseHTTPRequestHandler):
	def _set_headers(self):
		self.send_response(200)
		self.send_header('Content-type', 'text/plain')
		self.end_headers()

	def do_GET(self):
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


if __name__ == "__main__":
	db_setup(DB_URI)

	httpd = SimpleServer(('', PORT), Handler)
	httpd.serve_forever()
