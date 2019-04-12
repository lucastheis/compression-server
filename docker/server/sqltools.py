__all__ = [
	'db_setup',
	'db_add_team',
	'db_get_password',
	'db_add_submission',
	'db_check_exists',
	'db_count_recent_submissions',
	'db_get_results',
	'db_connect']

import os
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import sessionmaker
from collections import defaultdict

Base = declarative_base()
Session = sessionmaker()

class Team(Base):
	__tablename__ = 'teams'

	name = Column(String(128), primary_key=True)
	password = Column(String(64))
	email = Column(String(128))


class Submission(Base):
	__tablename__ = 'submissions'

	id = Column(Integer, primary_key=True)
	timestamp = Column(DateTime, server_default=func.now())
	name = Column(String(128))
	addr = Column(String(128))
	psnr = Column(Float)
	msssim = Column(Float)
	images_size = Column(Integer)
	decoding_time = Column(Integer)
	decoder_size = Column(Integer)
	decoder_hash = Column(String(64))
	task = Column(String(64))
	phase = Column(String(64))


def db_setup(dburi):
	engine = create_engine(dburi, echo=bool(os.environ.get('DEBUG')), pool_pre_ping=True)

	Session.configure(bind=engine)

	# create tables which do not yet exist
	Base.metadata.create_all(engine)


def db_connect():
	session = Session()
	return session


def db_add_team(db, name, password, email):
	team = Team(name=name, password=password, email=email)
	db.add(team)
	db.commit()


def db_get_password(db, name):
	passwords = db.query(Team).filter(Team.name == name).all()
	
	if len(passwords) == 1:
		return passwords[0].password


def db_add_submission(db, name, addr, psnr, msssim, images_size, decoding_time, decoder_size, decoder_hash, task, phase):
	submission = Submission(
		name=name,
		addr=addr,
		psnr=psnr,
		msssim=msssim,
		images_size=images_size,
		decoding_time=decoding_time,
		decoder_size=decoder_size,
		decoder_hash=decoder_hash,
		task=task,
		phase=phase)
	db.add(submission)
	db.commit()


def db_check_exists(db, decoder_hash):
	return db.query(Submission).filter(Submission.decoder_hash == decoder_hash).count() > 0


def db_count_recent_submissions(db, name):
	day_ago = datetime.utcnow() - timedelta(days=1)
	return db.query(Submission).filter(
		Submission.name == name,
		Submission.timestamp > day_ago).count()


def db_get_results(db, task, phase):
	q = db.query(Submission).filter(Submission.phase == phase, Submission.task == task)

	results = defaultdict(lambda: {'psnr': -np.inf, 'images_size': np.inf, 'datetime': datetime.min})

	for row in q.all():
		replace = False
		if phase == 'test' and row.timestamp > results[row.name]['datetime']:
			# in test phase, keep latest entry
			replace = True
		elif task != 'transparent' and row.psnr > results[row.name]['psnr']:
			# in low-rate track, keep entry with best PSNR
			replace = True
		elif task == 'transparent' and row.images_size < results[row.name]['images_size']:
			# in transparent track, keep entry with best MS-SSIM
			replace = True

		if replace:
			results[row.name] = {
				'datetime': row.timestamp,
				'psnr': row.psnr,
				'msssim': row.msssim,
				'images_size': row.images_size,
				'decoding_time': row.decoding_time,
				'decoder_size': row.decoder_size}

	# convert timestamps to string representation of date
	for row in results:
		results[row]['datetime'] = str(results[row]['datetime'])

	return dict(results)
