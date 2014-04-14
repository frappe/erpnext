# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# SETUP:
# install pip install --upgrade google-api-python-client
#
# In Google API
# - create new API project
# - create new oauth2 client (create installed app type as google \
# 	does not support subdomains)
#
# in conf.py, set oauth2 settings
# gdrive_client_id
# gdrive_client_secret

from __future__ import unicode_literals
import httplib2
import os
import mimetypes
import frappe
import oauth2client.client
from frappe.utils import cstr
from frappe import _
from apiclient.discovery import build
from apiclient.http import MediaFileUpload

# define log config for google drive api's log messages
# basicConfig redirects log to stderr
import logging
logging.basicConfig()

@frappe.whitelist()
def get_gdrive_authorize_url():
	flow = get_gdrive_flow()
	authorize_url = flow.step1_get_authorize_url()
	return {
		"authorize_url": authorize_url,
	}

def upload_files(name, mimetype, service, folder_id):
	if not frappe.db:
		frappe.connect()
	file_name = os.path.basename(name)
	media_body = MediaFileUpload(name, mimetype=mimetype, resumable=True)
	body = {
		'title': file_name,
		'description': 'Backup File',
		'mimetype': mimetype,
		'parents': [{
			'kind': 'drive#filelink',
			'id': folder_id
		}]
	}
	request = service.files().insert(body=body, media_body=media_body)
	response = None
	while response is None:
		status, response = request.next_chunk()

def backup_to_gdrive():
	from frappe.utils.backups import new_backup
	if not frappe.db:
		frappe.connect()
	get_gdrive_flow()
	credentials_json = frappe.db.get_value("Backup Manager", None, "gdrive_credentials")
	credentials = oauth2client.client.Credentials.new_from_json(credentials_json)
	http = httplib2.Http()
	http = credentials.authorize(http)
	drive_service = build('drive', 'v2', http=http)

	# upload database
	backup = new_backup()
	path = os.path.join(frappe.local.site_path, "public", "backups")
	filename = os.path.join(path, os.path.basename(backup.backup_path_db))

	# upload files to database folder
	upload_files(filename, 'application/x-gzip', drive_service,
		frappe.db.get_value("Backup Manager", None, "database_folder_id"))

	# upload files to files folder
	did_not_upload = []
	error_log = []

	files_folder_id = frappe.db.get_value("Backup Manager", None, "files_folder_id")

	frappe.db.close()
	path = os.path.join(frappe.local.site_path, "public", "files")
	for filename in os.listdir(path):
		filename = cstr(filename)
		found = False
		filepath = os.path.join(path, filename)
		ext = filename.split('.')[-1]
		size = os.path.getsize(filepath)
		if ext == 'gz' or ext == 'gzip':
			mimetype = 'application/x-gzip'
		else:
			mimetype = mimetypes.types_map.get("." + ext) or "application/octet-stream"

		#Compare Local File with Server File
	  	children = drive_service.children().list(folderId=files_folder_id).execute()
	  	for child in children.get('items', []):
			file = drive_service.files().get(fileId=child['id']).execute()
			if filename == file['title'] and size == int(file['fileSize']):
				found = True
				break
		if not found:
			try:
				upload_files(filepath, mimetype, drive_service, files_folder_id)
			except Exception, e:
				did_not_upload.append(filename)
				error_log.append(cstr(e))

	frappe.connect()
	return did_not_upload, list(set(error_log))

def get_gdrive_flow():
	from oauth2client.client import OAuth2WebServerFlow
	from frappe import conf

	if not "gdrive_client_id" in conf:
		frappe.throw(_("Please set Google Drive access keys in {0}"),format("site_config.json"))

	flow = OAuth2WebServerFlow(conf.gdrive_client_id, conf.gdrive_client_secret,
		"https://www.googleapis.com/auth/drive", 'urn:ietf:wg:oauth:2.0:oob')
	return flow

@frappe.whitelist()
def gdrive_callback(verification_code = None):
	flow = get_gdrive_flow()
	if verification_code:
		credentials = flow.step2_exchange(verification_code)
		allowed = 1

	# make folders to save id
	http = httplib2.Http()
	http = credentials.authorize(http)
	drive_service = build('drive', 'v2', http=http)
	erpnext_folder_id = create_erpnext_folder(drive_service)
	database_folder_id = create_folder('database', drive_service, erpnext_folder_id)
	files_folder_id = create_folder('files', drive_service, erpnext_folder_id)

	frappe.db.set_value("Backup Manager", "Backup Manager", "gdrive_access_allowed", allowed)
	frappe.db.set_value("Backup Manager", "Backup Manager", "database_folder_id", database_folder_id)
	frappe.db.set_value("Backup Manager", "Backup Manager", "files_folder_id", files_folder_id)
	final_credentials = credentials.to_json()
	frappe.db.set_value("Backup Manager", "Backup Manager", "gdrive_credentials", final_credentials)

	frappe.msgprint(_("Updated"))

def create_erpnext_folder(service):
	if not frappe.db:
		frappe.connect()
	erpnext = {
		'title': 'erpnext',
		'mimeType': 'application/vnd.google-apps.folder'
	}
	erpnext = service.files().insert(body=erpnext).execute()
	return erpnext['id']

def create_folder(name, service, folder_id):
	database = {
		'title': name,
		'mimeType': 'application/vnd.google-apps.folder',
		'parents': [{
	       	'kind': 'drive#fileLink',
	       	'id': folder_id
	    }]
	}
	database = service.files().insert(body=database).execute()
	return database['id']

if __name__=="__main__":
	backup_to_gdrive()
