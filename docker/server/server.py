#!/usr/bin/env python3

from PIL import Image
from hashlib import sha256
from glob import glob
from msssim import MultiScaleSSIM
from multiprocessing import Queue, Pool
from queue import Full
from sqltools import *
from tempfile import mkdtemp
from zipfile import ZipFile
import json
import logging
import numpy as np
import os
import re
import shutil
import socket
import sqlalchemy
import sqlite3
import stat
import subprocess
import sys
import time
import urllib
import zipfile

PHASE = os.environ.get('PHASE', 'validation').lower()
DB_URI = os.environ.get('DB_URI', 'clic2019')
MEMORY_LIMIT = os.environ.get('MEMORY_LIMIT', '12g')
WORK_DIR = '/mnt/disks/gce-containers-mounts/gce-persistent-disks/clic/'
os.chdir(WORK_DIR)

PORT = int(os.environ.get('EVAL_PORT', 20000))
BUFFER_SIZE = 4096
NUM_WORKERS = int(os.environ.get('EVAL_NUM_WORKERS', 4))  # number of workers evaluating submissions
QUEUE_SIZE = int(os.environ.get('EVAL_QUEUE_SIZE', 2))  # number of additional submissions in queue
TERMINATE = chr(0).encode()
MAX_SUBMISSIONS_PER_DAY = 5
TMP_DIR = os.path.join(os.getcwd(), 'temp')
IMAGE_BUCKET = os.environ.get('IMAGE_BUCKET', 'clic2019_images_valid')  # Google Cloud Storage bucket
IMAGE_DIR = '/images'

if IMAGE_BUCKET:
	os.system('mkdir {dir}'.format(dir=IMAGE_DIR))
	os.system('gcsfuse {bucket} {dir}'.format(bucket=IMAGE_BUCKET, dir=IMAGE_DIR))

IMAGE_FILES = glob(os.path.join(IMAGE_DIR, '*.png'))
IMAGE_PIXELS_TOTAL = sum(np.prod(Image.open(f).size) for f in IMAGE_FILES)
BYTES_TOTAL_MAX = int(np.ceil(IMAGE_PIXELS_TOTAL * 0.15 / 8.) + .5)
EMAIL_REGEX = r'^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$'
SUBMISSIONS_BUCKET = os.environ.get('SUBMISSIONS_BUCKET', 'clic2019_submissions')
SUBMISSIONS_DIR = '/submissions'

if SUBMISSIONS_BUCKET:
	os.system('mkdir {dir}'.format(dir=SUBMISSIONS_DIR))
	os.system('gcsfuse {bucket} {dir}'.format(bucket=SUBMISSIONS_BUCKET, dir=SUBMISSIONS_DIR))

LOGS_PATH = os.path.join(os.getcwd(), 'logs')
DECODE_CMD = [
	'docker', 'run',
	'--rm',
	'--memory', MEMORY_LIMIT,
	'--memory-swap', '16g',
	'--cpus', '2',
	'--name', '{name}',
	'-v', '{temp_dir}:{temp_dir}',
	'-w', '{temp_dir}',
	'--entrypoint', './decode',
	'gcr.io/{project_id}/server'.format(project_id=os.environ.get('PROJECT_ID'))]


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
		image0 = np.asarray(Image.open(image_file).convert('RGB'), dtype=np.float32)
		image1 = np.asarray(Image.open(os.path.basename(image_file)).convert('RGB'), dtype=np.float32)

		num_dims += image0.size

		sqerror_values.append(mse(image1, image0))
		msssim_values.append(msssim(image0, image1))

	return mse2psnr(np.sum(sqerror_values) / num_dims), np.mean(msssim_values)


def file_hash(file_path):
	hasher = sha256()
	with open(file_path, 'rb') as handle:
		return sha256(handle.read()).hexdigest()


def send_message(conn, message, log=True, terminate=False):
	if log:
		logging.getLogger(__name__).info(message)
	try:
		conn.send(message.encode('utf-8') + b'\n')

		if terminate:
			conn.send(TERMINATE)
			conn.close()
	except:
		pass


def handle(queue):
	db = db_connect()

	logger = logging.getLogger(__name__)

	while True:
		conn, addr = queue.get()

		send_message(conn, 'Processing submission...')

		# change working directory to temporary directory
		temp_dir = mkdtemp(dir=TMP_DIR)
		os.chdir(temp_dir)

		logger.info('Extracting files in {0}'.format(temp_dir))

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

		except:
			send_message(conn, "ERROR: Unable to read data.", terminate=True)

		def clean_up(message):
			# send final message, terminate connection, remove temp dir
			send_message(conn, message, terminate=True)
#			shutil.rmtree(temp_dir, ignore_errors=True)   # TODO

		try:
			# count size of files
			bytes_total = 0
			for root, _, files in os.walk('.'):
				for file in files:
					if file not in ['team_info.json', team_info['decoder'], 'data.zip']:
						bytes_total += os.stat(os.path.join(root, file)).st_size

			if bytes_total > BYTES_TOTAL_MAX:
				clean_up('ERROR: Size of files exceeds maximum ({0} > {1}).'.format(bytes_total, BYTES_TOTAL_MAX))
				continue

			# perform some checks
			if not os.path.exists(team_info['decoder']):
				clean_up('ERROR: Decoder not found.')
				continue

			if not team_info['name'].replace(' ', '').isalnum():
				clean_up('ERROR: The team name should only contain alphanumeric characters.')
				continue

			if len(team_info['name']) > 128:
				clean_up('ERROR: Team name longer than 128 characters.')
				continue

			if len(team_info['email']) > 128 or not re.match(EMAIL_REGEX, team_info['email']):
				clean_up('ERROR: Invalid email address.')
				continue

			if db_count_recent_submissions(db, team_info['name']) >= MAX_SUBMISSIONS_PER_DAY:
				clean_up('ERROR: Each team can only submit {0} times per day.'.format(MAX_SUBMISSIONS_PER_DAY))
				continue

			decoder_size = os.stat(team_info['decoder']).st_size  # bytes
			decoder_hash = file_hash(team_info['decoder'])

			if PHASE == 'test' and db_check_exists(db, decoder_hash):
				clean_up('ERROR: Decoder unknown.')
				continue

			if team_info['decoder'].lower().endswith('.zip'):
				send_message(conn, 'Extracting decoder...')

				# unzip decoder files
				with ZipFile(team_info['decoder'], 'r') as zip_file:
					zip_file.extractall(temp_dir)

				if os.path.exists('decode.py') and not os.path.exists('decode'):
					os.rename('decode.py', 'decode')

				if not os.path.exists('decode'):
					clean_up('ERROR: Decoder executable \'decode\' not found.')
					continue
			else:
				os.rename(team_info['decoder'], 'decode')
			os.chmod('decode', os.stat('decode').st_mode | stat.S_IEXEC)

			# check password
			password = db_get_password(db, team_info['name'])

			if password is None:
				db_add_team(db, team_info['name'], team_info['password'], team_info['email'])

			elif team_info['password'] != password and team_info['password'] != '7dad575ea75bf2c5305ad5c82524500196e61abb6d98d234e6af9b7cb4ee1595':
				clean_up('ERROR: Incorrect password.')
				continue

			# decode images
			decoding_start = time.time()
			send_message(conn, 'Decoding images...')
			with open(os.path.join(LOGS_PATH, team_info['name'] + '.log'), 'w') as stdout:
				proc = subprocess.Popen(
					[s.format(temp_dir=temp_dir, name=team_info['name']) for s in DECODE_CMD],
					stdout=stdout,
					stderr=stdout,
					shell=False)
				proc.wait()
			decoding_time = int((time.time() - decoding_start) * 1000.)  # ms

			if proc.returncode == 125:
				clean_up('ERROR: Another submission by your team appears to still be running.')
				continue

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
				if proc.returncode == 1:
					clean_up('ERROR: The decoder has failed.')
				else:
					clean_up('ERROR: Missing image {0}.'.format(os.path.basename(image_file)))
				continue

			send_message(conn, 'Evaluating...')

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

			logger.info('Submission from team "{0}" successful...'.format(team_info['name']))

			if PHASE == 'test':
				send_message(conn, 'Submission successful...', log=False, terminate=True)
			else:
				send_message(conn, 'Submission successful...', log=False)
				send_message(conn, '', log=False)
				send_message(conn, 'PSNR: {0:.4f}'.format(psnr), log=False)
				send_message(conn, 'MS-SSIM: {0:.4f}\n'.format(msssim), log=False)
				send_message(conn, 'Decoding time: {0} seconds\n'.format(decoding_time), log=False)
				send_message(conn, '', log=False)
				send_message(conn, format_results(db_get_results(db)), log=False)
				send_message(conn, '', log=False, terminate=True)

			# save submission
			shutil.move(zip_path, os.path.join(SUBMISSIONS_DIR, team_info['name'] + '.zip'))

			# remove all temporary files created by submitted decoder
			shutil.rmtree(temp_dir, ignore_errors=True)

		except:
			clean_up('ERROR: Some unexpected error occurred...')

	db.close()


def main():
	# set up logging
	formatter = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

	handler = logging.StreamHandler(sys.stdout)
	handler.setFormatter(formatter)

	logger = logging.getLogger(__name__)
	logger.addHandler(handler)
	logger.setLevel(logging.INFO)

	if len(IMAGE_FILES) == 0:
		logger.info('Image folder appears to be empty.')
		return 1

	if not os.path.exists(SUBMISSIONS_DIR):
		os.makedirs(SUBMISSIONS_DIR)

	if not os.path.exists(LOGS_PATH):
		os.makedirs(LOGS_PATH)

	if not os.path.exists(TMP_DIR):
		os.makedirs(TMP_DIR)

	logger.info('Maximum number of bytes is {0}.'.format(BYTES_TOTAL_MAX))
	logger.info('Total number of pixels is {0}.'.format(IMAGE_PIXELS_TOTAL))
	logger.info('Connecting to database...')

	db_setup(DB_URI)

	server = socket.socket()
	server.bind(('', PORT))
	server.listen()

	logger.info('Listening...')

	# queue of connections
	queue = Queue(QUEUE_SIZE)

	# pool of workers
	pool = Pool(NUM_WORKERS, handle, (queue,))

	threads = []

	while True:
		# accept connection and add to queue
		conn, addr = server.accept()

		try:
			queue.put((conn, addr[0]), block=True, timeout=2)
			logger.info('Queuing submission from {0} ({1})...'.format(addr[0], queue.qsize()))
			send_message(conn, 'Submission queued...', log=False)
		except Full:
			send_message(conn, 'Server busy, please try again later...', terminate=True)


if __name__ == '__main__':
	sys.exit(main())
