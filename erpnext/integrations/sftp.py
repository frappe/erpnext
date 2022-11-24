from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint, flt, get_bench_path, get_datetime, get_site_path, add_days
import paramiko
import sys, hashlib, os, signal, errno, logging, traceback
from stat import S_ISDIR
from time import sleep
import csv
from erpnext.accounts.doctype.bank_payment_settings.bank_payment_settings import get_upload_path

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

class SftpClient:
	_connection = None

	def __init__(self, settings):
		self.settings = settings
		self.create_connection(self.settings)

	@classmethod
	def create_connection(cls, settings):
		transport = paramiko.Transport(sock=(settings.hostname, settings.port))
		
		if settings.connection_type == "Normal":
			transport.connect(username = settings.username, password = settings.get_password("password"))
		else:
			k = paramiko.RSAKey.from_private_key_file(get_bench_path()+"/"+settings.private_key_path.strip("/"))
			transport.connect(username = settings.username, pkey = k)
		cls._connection = paramiko.SFTPClient.from_transport(transport)

	@staticmethod
	def uploading_info(uploaded_file_size, total_file_size):
		logging.info('uploaded_file_size : {} total_file_size : {}'.format(uploaded_file_size, total_file_size))

	def upload(self, local_path, remote_path):
		self._connection.put(localpath=local_path,
							remotepath=remote_path,
							callback=self.uploading_info,
							confirm=True)

	def file_exists(self, remote_path):
		try:
			logging.info("remote_path : {}".format(remote_path))
			self._connection.stat(remote_path)
		except IOError as e:
			if e.errno == errno.ENOENT:
				return False
			raise
		else:
			return True

	def download(self, remote_path, local_path, retry=5):
		if self.file_exists(remote_path) or retry == 0:
			self._connection.get(remote_path, local_path, callback=None)
		elif retry > 0:
			sleep(5)
			retry = retry - 1
			self.download(remote_path, local_path, retry=retry)

	def close(self):
		self._connection.close()

	def printTotals(self, transferred, toBeTransferred):
		print("Transferred: {}\tOut of: {}".format(transferred, toBeTransferred))

	def mkdir_p(self, remote_directory):
		if remote_directory == '/':
			self._connection.chdir('/')
			return
		if remote_directory == '':
			return
		try:
			self._connection.chdir(remote_directory)
		except IOError:
			dirname, basename = os.path.split(remote_directory.rstrip('/'))
			self.mkdir_p(dirname)
			self._connection.mkdir(basename)
			self._connection.chdir(basename)
			return True

	def upload_list(self, filelist=[]):
		# validate upload path
		upload_path = ''
		if not self.bps.upload_path:
			frappe.throw(_("<code><b>`File Upload Path`</b> is not set under <b>`Bank Payment Settings`</b></code>"))
		upload_path = get_upload_path(self.settings.upload_path)
		upload_path = str(upload_path).rstrip('/')

		paramiko.util.log_to_file("dhi.log")
		self.mkdir_p(upload_path)
		for f in filelist:
			src = f[0].rstrip('/')
			dest = os.path.basename(f[1].rstrip('/'))
			self.upload(local_path=src, remote_path=dest)

	def listdir(self, remote_path):
		return self._connection.listdir(remote_path)
