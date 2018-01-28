from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import sqlite3

DBNAME = 'clic2018_validation.db'


def db_get_results(db):
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

class Handler(BaseHTTPRequestHandler):
	def _set_headers(self):
		self.send_response(200)
		self.send_header('Content-type', 'text/plain')
		self.end_headers()

	def do_GET(self):
		db = sqlite3.connect(DBNAME)

		results = db_get_results(db)

		self._set_headers()
		self.wfile.write(b'window.leaderboard = ')
		self.wfile.write(json.dumps(results).encode())

	def do_HEAD(self):
		self._set_headers()

if __name__ == "__main__":
	httpd = HTTPServer(('', 8000), Handler)
	httpd.serve_forever()
