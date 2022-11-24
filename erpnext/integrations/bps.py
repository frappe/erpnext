from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint, flt, get_bench_path, get_datetime, get_site_path, add_days
from erpnext.accounts.doctype.bank_payment_settings.bank_payment_settings import get_upload_path
import paramiko
import sys, hashlib, os, signal, errno, logging, traceback
from stat import S_ISDIR
from time import sleep
import csv

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

class SftpClient:
	_connection = None

	def __init__(self, bank):
		self.bps = frappe.get_doc("Bank Payment Settings", bank)
		self.create_connection(self.bps)

	@classmethod
	def create_connection(cls, bps):
		transport = paramiko.Transport(sock=(bps.hostname, bps.port))
		
		if bps.connection_type == "Normal":
			transport.connect(username = bps.username, password = bps.get_password("password"))
		else:
			k = paramiko.RSAKey.from_private_key_file(get_bench_path()+"/"+bps.private_key_path.strip("/"))
			transport.connect(username = bps.username, pkey = k)
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
			time.sleep(5)
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
		upload_path = get_upload_path(self.bps.upload_path)
		upload_path = str(upload_path).rstrip('/')

		paramiko.util.log_to_file("bps.log")
		self.mkdir_p(upload_path)
		for f in filelist:
			src = f[0].rstrip('/')
			dest = os.path.basename(f[1].rstrip('/'))
			self.upload(local_path=src, remote_path=dest)

	def listdir(self, remote_path):
		return self._connection.listdir(remote_path)

@frappe.whitelist()
def test_connectivity(bank):
	if not frappe.db.exists('Bank Payment Settings', bank):
		frappe.msgprint(_("Data not found in Bank Payment Settings"))
	sftp = SftpClient(bank)
	sftp.close()
	print('Connection successful...')
	frappe.msgprint('Connection successful...')
 
def get_files_waiting_ack():
	''' get list of files waiting for acknowledgement '''
	
	waiting_ack = frappe.db.sql_list("""SELECT file_name 
		FROM `tabBank Payment Upload`
		WHERE docstatus = 1
		AND (status = 'Waiting Acknowledgement' OR 
				(status = 'Processing Acknowledgement' AND TIMESTAMPDIFF(MINUTE, IFNULL(last_updated,NOW()), NOW()) > 5))
		""")

	waiting_ack_formatted = {}
	next_day = None
	for file in waiting_ack:
		f = file.split('_')
		if f[0] == 'PEMSPAY':
			waiting_ack_formatted.setdefault('-'.join([f[1][:4], f[1][4:6]]), {}).setdefault('-'.join([f[1][:4], f[1][4:6], f[1][6:]]),[]).append(file)
			next_day = str(add_days('-'.join([f[1][:4], f[1][4:6], f[1][6:]]), 1))	
		elif f[0] == 'BULK':
			waiting_ack_formatted.setdefault('-'.join([f[2][:4], f[2][4:6]]), {}).setdefault('-'.join([f[2][:4], f[2][4:6], f[2][6:]]),[]).append(file)
			next_day = str(add_days('-'.join([f[2][:4], f[2][4:6], f[2][6:]]), 1))
		elif f[0] == 'INR':
			waiting_ack_formatted.setdefault('-'.join([f[3][4:], f[3][2:4]]), {}).setdefault('-'.join([f[3][4:], f[3][2:4], f[3][:2]]),[]).append(file)
			next_day = str(add_days('-'.join([f[3][4:], f[3][2:4], f[3][:2]]), 1))

		waiting_ack_formatted.setdefault('-'.join([next_day[:4], next_day[5:7]]), {}).setdefault('-'.join([next_day[:4], next_day[5:7], next_day[8:]]),[]).append(file)
	frappe.db.commit()
	return waiting_ack_formatted

@frappe.whitelist()
def process_files(bank='BOBL'):
	''' download the acknowledgement files from bank and process and update the status accordingly '''
	print("#"*80)
	print("# Method : {}".format(__name__))
	print("# Info : Press Ctrl+C to terminate the process")
	print("# PID: {}".format(os.getpid()))
	print("#"*80)
	remote_base = frappe.db.get_value('Bank Payment Settings', bank, 'acknowledgement_path')

	try:
		while True:
			logging.info("*** update_file_status started ***")
			waiting_list = get_files_waiting_ack()
			if not waiting_list:
				logging.info("No files found waiting for acknowledgement")
				sleep(60)
				continue

			try:
				sftp = SftpClient(bank)
			except Exception as e:
				logging.critical("CONNECTION_FAILURE {}".format(traceback.format_exc()))
				logging.info("Re-trying to connect ...")
				sleep(10)
				continue
			logging.info("Files waiting for acknowledgement: {}".format(waiting_list))

			local_list = []
			remote_list = []
			for m in waiting_list: # monthly folder list
				remote_path = '/'.join([str(remote_base),str(m)])
				if sftp.file_exists(remote_path):
					for d in waiting_list[m]: # daily folder list
						remote_path = '/'.join([str(remote_base),str(m),str(d)])
						if sftp.file_exists(remote_path):
							local_list  += [i.replace('.csv','_VALSUC.csv') if i.endswith('.csv') else i.replace('.txt','_SUC.txt') for i in waiting_list[m][d]]
							local_list  += [i.replace('.csv','_VALERR.csv') if i.endswith('.csv') else i.replace('.txt','_ERR.txt') for i in waiting_list[m][d]]
							remote_list = sftp.listdir(remote_path)
							download_list = list(set(local_list).intersection(remote_list))

							# create local directories
							filepath = get_site_path('private','files','epayment','processed').rstrip("/")+"/"
							if not os.path.exists(filepath):
								os.makedirs(filepath)
							
							# download the files from bank and process
							if download_list:
								logging.info("Acknowledgement found for : {}".format(download_list))
								for file in download_list:
									file_name = file.replace('_VALSUC','').replace('_VALERR','').replace('_SUC','').replace('_ERR','')
									if not frappe.db.exists('Bank Payment Upload', {'file_name': file_name}):
										continue
									update_bank_payment_status(file_name=file_name, file_status='Processing Acknowledgement', bank=bank, ack_file=None)								

									# download the acknowledgement file						
									try:
										sftp.download(remote_path='/'.join([remote_path, file]),
											local_path = '/'.join([filepath, file]))
									except Exception as e:
										logging.error("DOWNLOAD_FAILED {}".format(traceback.format_exc()))
									else:
										''' read the acknowledgement file and update status '''
										downloaded_file = '/'.join([filepath, file])
										file_status = str(downloaded_file).split('_')[-1].lower()
										if file_status in ('valsuc.csv', 'suc.txt'):
											update_bank_payment_status(file_name=file_name, file_status='Completed', bank=bank, ack_file=downloaded_file)
										elif file_status in ('valerr.csv', 'err.txt'):
											update_bank_payment_status(file_name=file_name, file_status='Failed', bank=bank, ack_file=downloaded_file)
							else:
								# update last_updated time if no acknowledgement files found at bank
								logging.info("No acknowledgement found ...") 
								local_list = list(set([i.replace('_VALSUC','').replace('_VALERR','').replace('_SUC','').replace('_ERR','') for i in local_list]))
								for file_name in local_list:
									if not frappe.db.exists('Bank Payment Upload', {'file_name': file_name}):
										continue
									update_bank_payment_status(file_name=file_name, file_status=None, bank=bank, ack_file=None)
			frappe.db.commit()
			sftp.close()
			sleep(60)
	except KeyboardInterrupt:
		print("INFO : Press Ctrl+C to terminate the process")
		if sftp: sftp.close()

def update_bank_payment_status(file_name, file_status, bank, ack_file=None):
	''' update status of the file '''
	if not frappe.db.exists('Bank Payment Upload', {'file_name': file_name}):
		return
	
	processing = completed = failed = 0
	doc = frappe.get_doc('Bank Payment', frappe.db.get_value('Bank Payment Upload', {'file_name': file_name}, "parent"))
	doc_modified = 0	
	# update status in Bank Payment Upload
	for rec in doc.uploads:
		status = rec.status
		if rec.file_name and file_name and rec.file_name.lower() == file_name.lower():
			doc_modified += 1
			bpu = frappe.get_doc('Bank Payment Upload', rec.name)
			bpu.db_set('last_updated', get_datetime())
			# rec.last_updated = get_datetime()
			if file_status:
				# rec.status = file_status
				bpu.db_set('status', file_status)
				status = file_status

		if status == 'Processing Acknowledgement':
			processing += 1
		elif status == 'Failed':
			failed += 1
		elif status == 'Completed':
			completed += 1

	# update status in Bank Payment Item
	# data = []
	# if ack_file:
	# 	with open(ack_file, 'rb') as localfile:
	# 		data = list(csv.reader(localfile))

	counter = 0
	for rec in doc.items:
		if rec.file_name and file_name and rec.file_name.lower() == file_name.lower():
			if file_status:
				doc_modified += 1
				bpi = frappe.get_doc('Bank Payment Item', rec.name)
				bpi.db_set('status', file_status)
				# rec.status = file_status
    
			# if rec.file_name.startswith('PEMSPAY') and rec.bank_name = bank:
			# 	rec.error 

	# update status in Bank Payment
	status = None
	if processing:
		status = 'Processing Acknowledgement'
	elif completed and failed:
		status = 'Partial Payment'
	elif completed:
		status = 'Completed'
	elif failed:
		status = 'Failed'

	if status or doc_modified:
		# doc.status = status if status else doc.status
		# doc.workflow_state = doc.status
		# doc.save(ignore_permissions=True)
		doc.reload()
		doc.db_set('status', status if status else doc.status)
		doc.db_set('workflow_state', status if status else doc.status)
		doc.reload()
		doc.update_transaction_status()
		doc.reload()

def check_kill_process(pstring):
	for line in os.popen("ps ax | grep " + pstring + " | grep -v grep"):
		fields = line.split()
		pid = fields[0]
		os.kill(int(pid), signal.SIGKILL)

def save_file():
	pass

def get_content_hash(filepath):
	BUF_SIZE = 65536
	md5 = hashlib.md5()
	
	with open(filepath, 'rb') as f:
		while True:
			data = f.read(BUF_SIZE)
			if not data:
				break
			md5.update(data)
	return md5.hexdigest()