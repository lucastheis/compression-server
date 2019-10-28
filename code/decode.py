#!/usr/bin/env python3

"""
This script executes a submission by doing the following:

	1. Mount storage bucket containing the submission
	2. Copy submission to an executable directory on the host (/var/lib/docker)
	3. Run the decoder
	4. Copy files generated by decoder back to the storage bucket
"""

import os
import sys
import traceback
from argparse import ArgumentParser
from subprocess import run, CalledProcessError, TimeoutExpired, PIPE, DEVNULL
from utils import get_logger
from zipfile import ZipFile

DECODE_CMD_CPU = [
	'docker', 'run',
	'--network', 'none',
	'--memory', '{memory_limit}',
	'--memory-swap', '{memory_limit}',
	'--cpus', '{num_cpus}',
	'--name', '{identifier}',
	'-v', '{work_dir}:/home/{identifier}',
	'-w', '/home/{identifier}',
	'-e', 'TF_CPP_MIN_LOG_LEVEL=3',
	'--entrypoint', './decode',
	'{image}']

DECODE_CMD_GPU = [
	'docker', 'run',
	'--network', 'none',
	'--memory', '{memory_limit}',
	'--memory-swap', '{memory_limit}',
	'--cpus', '{num_cpus}',
	'--name', '{identifier}',
	'-v', '{work_dir}:/home/{identifier}',
	'-v', '/home/kubernetes/bin/nvidia:/usr/local/nvidia:ro',
	'-v', '/home/kubernetes/bin/nvidia/vulkan/icd.d:/etc/vulkan/icd.d:ro',
	'--device', '/dev/nvidia0:/dev/nvidia0:mrw',
	'--device', '/dev/nvidiactl:/dev/nvidiactl:mrw',
	'--device', '/dev/nvidia-uvm:/dev/nvidia-uvm:mrw',
	'--device', '/dev/nvidia-uvm-tools:/dev/nvidia-uvm-tools:mrw',
	'-w', '/home/{identifier}',
	'-e', 'TF_CPP_MIN_LOG_LEVEL=3',
	'--entrypoint', './decode',
	'{image}']

DECODE_CMD = {True: DECODE_CMD_GPU, False: DECODE_CMD_CPU}


def main(args):
	logger = get_logger(debug=args.debug)

	# directory on host in which decoder will be run
	identifier = args.task + '_' + args.phase + '_' + args.team
	work_dir = os.path.join(args.exec_dir, identifier)

	# mount submission
	try:
		logger.info('Obtaining submission')
		submission_dir = '/submission'
		run('mkdir -p {dir}'.format(dir=submission_dir), shell=True)
		run('gcsfuse --implicit-dirs --file-mode 777 --only-dir {subdir} {bucket} {dir}'.format(
				subdir=os.path.join(args.task, args.phase, args.team),
				bucket=args.submission_bucket,
				dir=submission_dir),
			stdout=PIPE,
			stderr=PIPE,
			check=True,
			shell=True)
	except CalledProcessError as error:
		logger.error('Unable to mount submission bucket')
		logger.debug(error.stderr)
		return 1

	# mount environment files
	try:
		environment_dir = '/environment'
		run('mkdir -p {}'.format(environment_dir), shell=True)
		run('gcsfuse --implicit-dirs --file-mode 777 --only-dir {subdir} {bucket} {dir}'.format(
				subdir=os.path.join(args.task, args.phase),
				bucket=args.environment_bucket,
				dir=environment_dir),
			stdout=PIPE,
			stderr=PIPE,
			check=True,
			shell=True)
	except CalledProcessError as error:
		logger.error('Unable to mount environment bucket')
		logger.debug(error.stderr)
		run('fusermount -u {}'.format(submission_dir), shell=True)
		return 1

	try:
		# copy files to executable working directory
		logger.info('Copying submission')
		run('mkdir -p {dir}'.format(dir=work_dir), check=True, shell=True)
		run('rsync -r {source}/ {target}/'.format(source=environment_dir, target=work_dir),
			shell=True)
		run('rsync -r {source}/ {target}/'.format(source=submission_dir, target=work_dir),
			shell=True)
		run('sync', shell=True)

		# unzip decoder if zipped
		zip_path = os.path.join(work_dir, 'decoder.zip')
		if os.path.exists(zip_path):
			logger.info('Unzipping decoder')
			ZipFile(zip_path).extractall(work_dir)

		# check if decoder executable is present
		if not os.path.exists(os.path.join(work_dir, 'decode')):
			logger.error('Missing executable \'decode\'')
			return 1

		# make sure latest Docker image is present before decoder starts
		try:
			logger.info('Pulling Docker image')
			run('docker pull {} > /dev/null'.format(args.image), stdout=PIPE, stderr=PIPE, check=True, shell=True)
		except CalledProcessError as error:
			logger.warn('Failed to pull Docker image')
			logger.debug(error.stdout)
			logger.debug(error.stderr)

		# delete container if for some reason it already exists
		containers = run('docker ps -a --format {{.Names}}',
			stdout=PIPE, stderr=DEVNULL, check=True, shell=True).stdout
		if identifier in containers.decode().split():
			logger.debug('Removing existing container')
			run('docker stop {}'.format(identifier),
				stdout=PIPE, stderr=PIPE, check=True, shell=True)
			run('docker rm {}'.format(identifier),
				stdout=PIPE, stderr=PIPE, check=True, shell=True)

		try:
			decode_cmd = [
				s.format(
					work_dir=work_dir,
					identifier=identifier,
					**vars(args))
				for s in DECODE_CMD[args.gpu]]

			# run decoder
			logger.info('Running decoder')
			run(decode_cmd, timeout=args.timeout, check=True, shell=False)
			logger.info('Decoding complete')

		except CalledProcessError as error:
			if error.returncode == 125:
				logger.error('Unable to start Docker container')
				logger.debug(error)
				return 1

			elif error.returncode == 137:
				# check if process was killed by OOMKiller
				process = run('docker inspect {}'.format(identifier),
					stdout=PIPE, stderr=PIPE, check=True, shell=True)

				if '"OOMKilled": true' in process.stdout.decode():
					logger.error('The decoder exceeded the memory limit ({})'.format(
						args.memory_limit))
					return 1

			logger.error('The decoder has failed ({})'.format(error.returncode))
			logger.debug(error)
			return 1

		except TimeoutExpired:
			logger.error('Decoding exceeded the time limit ({} seconds)'.format(args.timeout))
			return 1

		finally:
			# remove docker container
			run('docker rm {}'.format(identifier),
				stderr=PIPE, stdout=PIPE, check=True, shell=True)

	except:
		logger.error('Some unexpected error occured')
		logger.debug(traceback.format_exc())
		return 1

	finally:
		# copy (intermediate) results back to submission directory
		run('rsync -r {source}/ {target}/'.format(source=work_dir, target=submission_dir),
			shell=True)
		run('sync', shell=True)

		# remove working directory
		run('rm -rf {}'.format(work_dir), shell=True)

		# unmount buckets
		run('fusermount -u {}'.format(submission_dir), shell=True)
		run('fusermount -u {}'.format(environment_dir), shell=True)

	return 0


if __name__ == '__main__':
	parser = ArgumentParser()
	parser.add_argument('--submission_bucket', type=str, required=True,
		help='Name of the bucket which contains submissions')
	parser.add_argument('--environment_bucket', type=str, required=True,
		help='Name of the bucket which contains any extra files provided to decoders')
	parser.add_argument('--task', type=str, required=True)
	parser.add_argument('--phase', type=str, required=True)
	parser.add_argument('--team', type=str, required=True)
	parser.add_argument('--image', type=str, required=True,
		help='Docker image used to launch decoding process')
	parser.add_argument('--memory_limit', type=str, default='12g')
	parser.add_argument('--num_cpus', type=int, default=2)
	parser.add_argument('--exec_dir', type=str, default='/var/lib/docker/submissions',
		help='Location of executable directory which exists both on host and inside container')
	parser.add_argument('--debug', action='store_true')
	parser.add_argument('--timeout', type=int, default=None,
		help='Decoder is given this many seconds to complete')
	parser.add_argument('--gpu', action='store_true',
		help='Make GPU available to decoder')

	args = parser.parse_args()

	sys.exit(main(args))
