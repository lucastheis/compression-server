#!/usr/bin/env python3

from argparse import ArgumentParser
from hashlib import sha256
from tempfile import TemporaryFile
from zipfile import ZipFile
import os
import json
import re
import socket
import sys

HOST = 'eval.compression.cc'
PORT = 20000
BUFFER_SIZE = 4096
TERMINATE = chr(0).encode()


def main(args):
	if not args.name.replace(' ', '').isalnum():
		print('The team name should only contain alphanumeric characters.')
		return 1

	if len(args.name) > 128:
		print('Team name longer than 128 characters.')
		return 1

	if len(args.email) > 128:
		print('Please use an email address shorter than 128 characters.')
		return 1

	if not re.match(r'^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$', args.email):
		print('Invalid email address.')
		return 1

	if not len(args.password) >= 8:
		print('The password should be at least 8 characters long.')
		return 1

	print('Connecting...')

	# connect to evaluation server
	s = socket.socket()
	s.connect((HOST, PORT))

	with TemporaryFile() as temp_file:
		team_info = {
			'name': args.name,
			'email': args.email,
			'password': sha256(args.password.encode()).hexdigest(),
			'decoder': os.path.basename(args.decoder)}

		# create a zip archive containing all files
		zip_file = ZipFile(temp_file, 'w')
		zip_file.writestr('team_info.json', json.dumps(team_info))
		zip_file.write(args.decoder, os.path.basename(args.decoder))
		for image in args.images:
			zip_file.write(image)
		zip_file.close()

		# reset file
		temp_file.seek(0)

		# send archive
		print('Sending data...')

		for data in iter(lambda: temp_file.read(BUFFER_SIZE), b''):
			s.send(data)
		s.shutdown(socket.SHUT_WR)

		# wait for response
		for message in iter(lambda: s.recv(1), TERMINATE):
			sys.stdout.write(message.decode())
			sys.stdout.flush()

	s.close()

	return 0


if __name__ == '__main__':
	parser = ArgumentParser()
	parser.add_argument('decoder',
	        help='An executable decoder')
	parser.add_argument('images', nargs='+',
	        help='Compressed image files')
	parser.add_argument('--name', '-n', required=True,
		help='Your team\'s name')
	parser.add_argument('--password', '-p', required=True,
		help='A password needed for updating your team\'s results later')
	parser.add_argument('--email', '-e', required=True,
		help='An email address to reach your team')

	sys.exit(main(parser.parse_args()))
