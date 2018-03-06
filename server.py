#!/usr/bin/env python3

from PIL import Image
from hashlib import sha256
from glob import glob
from msssim import MultiScaleSSIM
from multiprocessing import Queue, Pool
from queue import Full
from tempfile import mkdtemp
from zipfile import ZipFile
import json
import numpy as np
import os
import re
import shutil
import socket
import sqlite3
import stat
import subprocess
import sys
import time

PORT = 20000
BUFFER_SIZE = 4096
NUM_THREADS = 4  # number of workers evaluating submissions
QUEUE_SIZE = 2  # number of additional submissions in queue
TERMINATE = chr(0).encode()
DBNAME = 'clic2018_validation.db'
MAX_SUBMISSIONS_PER_DAY = 5
TMP_DIR = os.path.join(os.getcwd(), 'temp')
IMAGE_DIR = '/images'
IMAGE_FILES = glob(os.path.join(IMAGE_DIR, '*.png'))
IMAGE_PIXELS_TOTAL = sum(np.prod(Image.open(f).size) for f in IMAGE_FILES)
BYTES_TOTAL_MAX = int(np.ceil(IMAGE_PIXELS_TOTAL * 0.15 / 8.) + .5)
SUBMISSIONS_PATH = os.path.join(os.getcwd(), 'submissions')
LOGS_PATH = os.path.join(os.getcwd(), 'logs')
DECODE_CMD = [
	'docker', 'run',
	'--rm',
	'--memory', '4g',
	'--cpus', '1',
	'-v', '{temp_dir}:{temp_dir}',
	'-w', '{temp_dir}',
	'clic2018/compression',
	'./decode']


def db_setup():
	db = sqlite3.connect(DBNAME)
	cursor = db.cursor()
	cursor.execute('''
		CREATE TABLE IF NOT EXISTS teams (
			name CHARACTER(128) PRIMARY KEY,
			password CHARACTER(64),
			email CHARACTER(128))''')
	cursor.execute('''
		CREATE TABLE IF NOT EXISTS submissions (
			timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
			name CHARACTER(128),
			addr CHARACTER(128),
			psnr DOUBLE,
			msssim DOUBLE,
			images_size INT,
			decoding_time INT,
			decoder_size INT,
			decoder_hash CHARACTER(64))''')
	db.commit()
	db.close()


def db_get_password(db, name):
	cursor = db.cursor()
	cursor.execute('SELECT password FROM teams WHERE name = "{0}"'.format(name))

	passwords = cursor.fetchall()

	if len(passwords) == 1:
		return passwords[0][0]


def db_create_team(db, name, password, email):
	cursor = db.cursor()
	cursor.execute('INSERT INTO teams VALUES ("{0}", "{1}", "{2}")'.format(name, password, email))
	db.commit()


def db_add_submission(db, name, addr, psnr, msssim, images_size, decoding_time, decoder_size, decoder_hash):
	cursor = db.cursor()
	cursor.execute('''
		INSERT INTO submissions (name, addr, psnr, msssim, images_size, decoding_time, decoder_size, decoder_hash)
		VALUES ("{0}", "{1}", {2}, {3}, {4}, {5}, {6}, "{7}")'''.format(
			name, addr, psnr, msssim, images_size, decoding_time, decoder_size, decoder_hash))
	db.commit()


def db_count_recent_submissions(db, name):
	cursor = db.cursor()
	cursor.execute('''
	SELECT COUNT(*) AS "count"
	FROM submissions
	WHERE timestamp > DATETIME("now", "-1 day") AND name = "{0}"'''.format(name))
	return cursor.fetchone()[0]


def db_get_results(db):
	cursor = db.cursor()
	cursor.execute('SELECT name, MAX(psnr), msssim, decoding_time, decoder_size, timestamp FROM submissions GROUP BY name ORDER BY psnr DESC')

	results = {}
	for name, psnr, msssim, decoding_time, decoder_size, timestamp in cursor.fetchall():
		results[name] = {'psnr': psnr, 'msssim': msssim, 'decoding_time': decoding_time, 'decoder_size': decoder_size}

	return results


def format_results(results):
	res_str = ['{0:<36} {1:<10} {2:<10}'.format('TEAM', 'PSNR', 'MS-SSIM')]
	for team_name, team_results in results.items():
		res_str.append('{0:<36} {1:<10.2f} {2:.3f}'.format(team_name[:32], team_results['psnr'], team_results['msssim']))
	return '\n'.join(res_str)


def mse(image0, image1):
	return np.sum(np.square(image1 - image0))


def mse2psnr(mse):
	return 20. * np.log10(255.) - 10. * np.log10(mse)


def msssim(image0, image1):
	return MultiScaleSSIM(image0[None], image1[None])


def evaluate(conn):
	num_dims = 0
	sqerror_values = []
	msssim_values = []

	connected = True

	for image_file in IMAGE_FILES:
		image0 = np.asarray(Image.open(image_file))
		image1 = np.asarray(Image.open(os.path.basename(image_file)))

		num_dims += image0.size

		sqerror_values.append(np.sum(np.square(image1 - image0)))
		msssim_values.append(msssim(image0, image1))

		try:
			if connected:
				conn.send(b'.')
		except:
			connected = False

	return mse2psnr(np.sum(sqerror_values) / num_dims), np.mean(msssim_values)


def file_hash(file_path):
	hasher = sha256()
	with open(file_path, 'rb') as handle:
		return sha256(handle.read()).hexdigest()


def handle(queue):
	db = sqlite3.connect(DBNAME)

	while True:
		conn, addr = queue.get()

		conn.send(b'Processing submission...\n')
		print('Processing submission...')

		# change working directory to temporary directory
		temp_dir = mkdtemp(dir=TMP_DIR)
		print('Extracting files in {0}'.format(temp_dir))
		os.chdir(temp_dir)

		try:
			# receive zip archive
			zip_path = './data.zip'
			with open(zip_path, 'wb') as handle:
				for data in iter(lambda: conn.recv(BUFFER_SIZE), b''):
					handle.write(data)

			# unzip
			with ZipFile(zip_path, 'r') as zip_file:
				team_info = json.loads(zip_file.read('team_info.json').decode())
				zip_file.extractall(temp_dir)

			# count size of files
			bytes_total = 0
			for root, _, files in os.walk('.'):
				for file in files:
					if file not in ['team_info.json', team_info['decoder'], 'data.zip']:
						bytes_total += os.stat(os.path.join(root, file)).st_size

			if bytes_total > BYTES_TOTAL_MAX:
				message = 'ERROR: Size of files exceeds maximum ({0} > {1}).'
				message = message.format(bytes_total, BYTES_TOTAL_MAX)
				print(message)
				conn.send((message + '\n').encode())
				conn.send(TERMINATE)
				conn.close()
				shutil.rmtree(temp_dir, ignore_errors=True)
				continue

			# perform some checks
			if not os.path.exists(team_info['decoder']):
				print('ERROR: Decoder not found.')
				conn.send(b'ERROR: Decoder not found.\n')
				conn.send(TERMINATE)
				conn.close()
				shutil.rmtree(temp_dir, ignore_errors=True)
				continue

			if not team_info['name'].replace(' ', '').isalnum():
				print('Invalid team name.')
				conn.send(b'ERROR: The team name should only contain alphanumeric characters.\n')
				conn.send(TERMINATE)
				conn.close()
				shutil.rmtree(temp_dir, ignore_errors=True)
				continue

			if len(team_info['name']) > 128:
				print('Invalid team name.')
				conn.send(b'ERROR: Team name longer than 128 characters.\n')
				conn.send(TERMINATE)
				conn.close()
				shutil.rmtree(temp_dir, ignore_errors=True)
				continue

			if len(team_info['email']) > 128 or not re.match(r'^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$', team_info['email']):
				print('Invalid email address.')
				conn.send(b'ERROR: Invalid email address.\n')
				conn.send(TERMINATE)
				conn.close()
				shutil.rmtree(temp_dir, ignore_errors=True)
				return 1

			if db_count_recent_submissions(db, team_info['name']) >= MAX_SUBMISSIONS_PER_DAY:
				print('Team "{0}" reached submission limit.'.format(team_info['name']))
				message = 'ERROR: Each team can only submit {0} times per day.\n'
				conn.send(message.format(MAX_SUBMISSIONS_PER_DAY).encode())
				conn.send(TERMINATE)
				conn.close()
				shutil.rmtree(temp_dir, ignore_errors=True)
				continue

			decoder_size = os.stat(team_info['decoder']).st_size  # bytes
			decoder_hash = file_hash(team_info['decoder'])

			if team_info['decoder'].lower().endswith('.zip'):
				print('Extracting decoder...')
				conn.send(b'Extracting decoder...\n')

				# unzip decoder files
				with ZipFile(team_info['decoder'], 'r') as zip_file:
					zip_file.extractall(temp_dir)

				if os.path.exists('decode.py') and not os.path.exists('decode'):
					os.rename('decode.py', 'decode')

				if not os.path.exists('decode'):
					print('ERROR: Decoder executable \'decode\' not found.')
					conn.send(b'ERROR: Decoder executable \'decode\' not found.\n')
					conn.send(TERMINATE)
					conn.close()
					shutil.rmtree(temp_dir, ignore_errors=True)
					continue
			else:
				os.rename(team_info['decoder'], 'decode')
			os.chmod('decode', os.stat('decode').st_mode | stat.S_IEXEC)

			# check password
			password = db_get_password(db, team_info['name'])

			if password is None:
				db_create_team(db, team_info['name'], team_info['password'], team_info['email'])

			elif team_info['password'] != password:
				print('Incorrect password.')
				conn.send(b'ERROR: Incorrect password.\n')
				conn.send(TERMINATE)
				conn.close()
				shutil.rmtree(temp_dir, ignore_errors=True)
				continue

			# decode images
			decoding_start = time.time()
			print('Decoding images...')
			conn.send(b'Decoding images...\n')
			with open(os.path.join(LOGS_PATH, team_info['name'] + '.log'), 'w') as stdout:
				proc = subprocess.Popen(
					[s.format(temp_dir=temp_dir) for s in DECODE_CMD],
					stdout=stdout,
					stderr=stdout,
					shell=False)
				proc.wait()
			decoding_time = int((time.time() - decoding_start) * 1000.)  # ms

			# move image files out of subdirectories
			for root, _, files in os.walk('.'):
				if root == '.':
					continue
				for file in files:
					if file.lower().endswith('.png'):
						os.rename(os.path.join(root, file), os.path.basename(file))

			# check if all images are present
			images_complete = False
			for image_file in IMAGE_FILES:
				if not os.path.exists(os.path.basename(image_file)):
					break
			else:
				images_complete = True

			if not images_complete:
				message = 'ERROR: Missing image {0}.'.format(os.path.basename(image_file))
				print(message)
				conn.send((message + '\n').encode())
				conn.send(TERMINATE)
				conn.close()
				shutil.rmtree(temp_dir, ignore_errors=True)
				continue

			print('Evaluating...')
			try:
				conn.send(b'Evaluating...')
			except:
				pass

			# evaluate decoded images
			psnr, msssim = evaluate(conn)

			db_add_submission(
				db,
				team_info['name'],
				addr,
				psnr,
				msssim,
				bytes_total,
				decoding_time,
				decoder_size,
				decoder_hash)

			print('Submission from team "{0}" successful...'.format(team_info['name']))

			try:
				conn.send(b'\n')
				conn.send(b'Submission successful...\n')
				conn.send(b'\n')
				conn.send('PSNR: {0:.4f}\n'.format(psnr).encode())
				conn.send('MS-SSIM: {0:.4f}\n'.format(msssim).encode())
				conn.send('Decoding time: {0} seconds\n'.format(decoding_time).encode())
				conn.send(b'\n')
				conn.send(format_results(db_get_results(db)).encode())
				conn.send(b'\n')
			except:
				pass

			shutil.move(zip_path, os.path.join(SUBMISSIONS_PATH, team_info['name'] + '.zip'))
			shutil.rmtree(temp_dir, ignore_errors=True)

			conn.send(TERMINATE)
			conn.close()

		except Exception as exception:
			print(exception)
			try:
				conn.send(b'ERROR: Some unexpected error occurred...\n')
				conn.send(TERMINATE)
				conn.close()
			except:
				pass
			shutil.rmtree(temp_dir, ignore_errors=True)

	db.close()


def main():
	if len(IMAGE_FILES) == 0:
		print('Image folder appears to be empty.')
		return 1

	if not os.path.exists(SUBMISSIONS_PATH):
		os.makedirs(SUBMISSIONS_PATH)

	if not os.path.exists(LOGS_PATH):
		os.makedirs(LOGS_PATH)

	print('Maximum number of bytes is {0}.'.format(BYTES_TOTAL_MAX))
	print('Total number of pixels is {0}.'.format(IMAGE_PIXELS_TOTAL))
	print('Connecting to database...')

	db_setup()

	server = socket.socket()
	server.bind(('', PORT))
	server.listen()

	print('Listening...')

	# queue of connections
	queue = Queue(QUEUE_SIZE)

	# pool of workers
	pool = Pool(NUM_THREADS, handle, (queue,))

	threads = []

	while True:
		# accept connection and add to queue
		conn, addr = server.accept()

		try:
			queue.put((conn, addr[0]), block=True, timeout=2)
			conn.send(b'Submission queued...\n')
			print('Queuing submission from {0}...'.format(addr[0]))
		except Full:
			conn.send(b'Server busy, please try again later...\n')
			conn.close()


if __name__ == '__main__':
	sys.exit(main())
