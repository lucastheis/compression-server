#!/usr/bin/env python3

from hashlib import sha256
import os
import sys
import sqlite3
from argparse import ArgumentParser

DBNAME = 'clic2018_test.db'

def file_hash(file_path):
	hasher = sha256()
	with open(file_path, 'rb') as handle:
		return sha256(handle.read()).hexdigest()

def db_check_exists(db, decoder_hash):
	cursor = db.cursor()
	cursor.execute('''
		SELECT COUNT(*) AS "count"
		FROM submissions
		WHERE decoder_hash = "{0}"'''.format(decoder_hash))
	return cursor.fetchone()[0] > 0

def db_add_submission(db, name, addr, psnr, msssim, images_size, decoding_time, decoder_size, decoder_hash):
	cursor = db.cursor()
	cursor.execute('''
		INSERT INTO submissions (name, addr, psnr, msssim, images_size, decoding_time, decoder_size, decoder_hash)
		VALUES ("{0}", "{1}", {2}, {3}, {4}, {5}, {6}, "{7}")'''.format(
			name, addr, psnr, msssim, images_size, decoding_time, decoder_size, decoder_hash))
	db.commit()


if __name__ == '__main__':
	parser = ArgumentParser()
	parser.add_argument('name')
	parser.add_argument('decoders', nargs='+')
	args = parser.parse_args()

	for decoder in args.decoders:
		decoder_hash = file_hash(decoder)
		decoder_size = os.stat(decoder).st_size  # bytes

		db = sqlite3.connect(DBNAME)

		if db_check_exists(db, decoder_hash):
			print('Decoder already exists in database')
			continue

		db_add_submission(db, args.name, '127.0.0.1', 0., 0., 0., 0., decoder_size, decoder_hash)

		db.close()
