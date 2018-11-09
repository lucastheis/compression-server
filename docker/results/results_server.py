#!/usr/bin/env python3

from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import json
import os
import sqlite3

TEST_PHASE = (os.environ.get('PHASE', 'validation') == 'test')

if TEST_PHASE:
	DBNAME = 'clic2018_test.db'
	PORT = 9000

	def db_get_results(db):
		order_by = 'psnr'

		cursor = db.cursor()
		cursor.execute('''
			SELECT name, psnr, msssim, decoding_time, decoder_size, images_size, MAX(timestamp)
			FROM submissions
			WHERE psnr > 0
			GROUP BY name
			ORDER BY timestamp DESC''')

		results = {}
		for name, psnr, msssim, decoding_time, decoder_size, images_size, timestamp in cursor.fetchall():
			results[name] = {
				'datetime': timestamp,
				'psnr': psnr,
				'msssim': msssim,
				'decoding_time': decoding_time,
				'decoder_size': decoder_size,
				'images_size': images_size}

		return results

else:
	DBNAME = 'clic2018_validation.db'
	PORT = 8000

	def db_get_results(db):
		order_by = 'psnr'

		cursor = db.cursor()
		cursor.execute('''
			SELECT name, MAX(psnr), msssim, decoding_time, decoder_size, images_size, timestamp
			FROM submissions
			GROUP BY name
			ORDER BY psnr DESC''')

		results = {}
		for name, psnr, msssim, decoding_time, decoder_size, images_size, timestamp in cursor.fetchall():
			results[name] = {
				'datetime': timestamp,
				'psnr': psnr,
				'msssim': msssim,
				'decoding_time': decoding_time,
				'decoder_size': decoder_size,
				'images_size': images_size}

		return results


class SimpleServer(ThreadingMixIn, HTTPServer):
	pass


class Handler(BaseHTTPRequestHandler):
	def _set_headers(self):
		self.send_response(200)
		self.send_header('Content-type', 'text/plain')
		self.end_headers()

	def do_GET(self):
		if self.path == '/':
			print('Connecting...')
			db = sqlite3.connect(DBNAME)

			print('Fetching results...')
			results = db_get_results(db)

			print('Sending headers...')
			self._set_headers()

			print('Sending content...')
			self.wfile.write(b'window.leaderboard = ')
			self.wfile.write(json.dumps(results).encode())

			print('Closing connection...')
			db.close()
			print('Done.')
		else:
			self.send_error(404)

	def do_HEAD(self):
		self._set_headers()


if __name__ == "__main__":
	httpd = SimpleServer(('', PORT), Handler)
	httpd.serve_forever()
