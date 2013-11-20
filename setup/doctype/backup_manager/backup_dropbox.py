# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# SETUP:
# install pip install --upgrade dropbox
#
# Create new Dropbox App
#
# in conf.py, set oauth2 settings
# dropbox_access_key
# dropbox_access_secret

from __future__ import unicode_literals
import os
import webnotes
from webnotes.utils import get_request_site_address, get_base_path, cstr
from webnotes import _

from backup_manager import ignore_list

@webnotes.whitelist()
def get_dropbox_authorize_url():
	sess = get_dropbox_session()
	request_token = sess.obtain_request_token()
	return_address = get_request_site_address(True) \
		+ "?cmd=setup.doctype.backup_manager.backup_dropbox.dropbox_callback"

	url = sess.build_authorize_url(request_token, return_address)

	return {
		"url": url,
		"key": request_token.key,
		"secret": request_token.secret,
	}

@webnotes.whitelist(allow_guest=True)
def dropbox_callback(oauth_token=None, not_approved=False):
	from dropbox import client
	if not not_approved:
		if webnotes.conn.get_value("Backup Manager", None, "dropbox_access_key")==oauth_token:		
			allowed = 1
			message = "Dropbox access allowed."

			sess = get_dropbox_session()
			sess.set_request_token(webnotes.conn.get_value("Backup Manager", None, "dropbox_access_key"), 
				webnotes.conn.get_value("Backup Manager", None, "dropbox_access_secret"))
			access_token = sess.obtain_access_token()
			webnotes.conn.set_value("Backup Manager", "Backup Manager", "dropbox_access_key", access_token.key)
			webnotes.conn.set_value("Backup Manager", "Backup Manager", "dropbox_access_secret", access_token.secret)
			webnotes.conn.set_value("Backup Manager", "Backup Manager", "dropbox_access_allowed", allowed)
			dropbox_client = client.DropboxClient(sess)
			try:
				dropbox_client.file_create_folder("files")
			except:
				pass

		else:
			allowed = 0
			message = "Illegal Access Token Please try again."
	else:
		allowed = 0
		message = "Dropbox Access not approved."

	webnotes.local.message_title = "Dropbox Approval"
	webnotes.local.message = "<h3>%s</h3><p>Please close this window.</p>" % message
	
	if allowed:
		webnotes.local.message_success = True
	
	webnotes.conn.commit()
	webnotes.response['type'] = 'page'
	webnotes.response['page_name'] = 'message.html'

def backup_to_dropbox():
	from dropbox import client, session
	from conf import dropbox_access_key, dropbox_secret_key
	from webnotes.utils.backups import new_backup
	if not webnotes.conn:
		webnotes.connect()

	sess = session.DropboxSession(dropbox_access_key, dropbox_secret_key, "app_folder")

	sess.set_token(webnotes.conn.get_value("Backup Manager", None, "dropbox_access_key"),
		webnotes.conn.get_value("Backup Manager", None, "dropbox_access_secret"))
	
	dropbox_client = client.DropboxClient(sess)

	# upload database
	backup = new_backup()
	filename = os.path.join(get_base_path(), "public", "backups", 
		os.path.basename(backup.backup_path_db))
	upload_file_to_dropbox(filename, "/database", dropbox_client)

	webnotes.conn.close()
	response = dropbox_client.metadata("/files")
	
	# upload files to files folder
	did_not_upload = []
	error_log = []
	path = os.path.join(get_base_path(), "public", "files")
	for filename in os.listdir(path):
		filename = cstr(filename)
		if filename in ignore_list:
			continue
		
		found = False
		filepath = os.path.join(path, filename)
		for file_metadata in response["contents"]:
 			if os.path.basename(filepath) == os.path.basename(file_metadata["path"]) and os.stat(filepath).st_size == int(file_metadata["bytes"]):
				found = True
				break
		if not found:
			try:
				upload_file_to_dropbox(filepath, "/files", dropbox_client)
			except Exception:
				did_not_upload.append(filename)
				error_log.append(webnotes.getTraceback())
	
	webnotes.connect()
	return did_not_upload, list(set(error_log))

def get_dropbox_session():
	try:
		from dropbox import session
	except:
		webnotes.msgprint(_("Please install dropbox python module"), raise_exception=1)
		
	try:
		from conf import dropbox_access_key, dropbox_secret_key
	except ImportError:
		webnotes.msgprint(_("Please set Dropbox access keys in") + " conf.py", 
		raise_exception=True)
	sess = session.DropboxSession(dropbox_access_key, dropbox_secret_key, "app_folder")
	return sess

def upload_file_to_dropbox(filename, folder, dropbox_client):
	from dropbox import rest
	size = os.stat(filename).st_size
	
	with open(filename, 'r') as f:
		# if max packet size reached, use chunked uploader
		max_packet_size = 4194304
	
		if size > max_packet_size:
			uploader = dropbox_client.get_chunked_uploader(f, size)
			while uploader.offset < size:
				try:
					uploader.upload_chunked()
					uploader.finish(folder + "/" + os.path.basename(filename), overwrite=True)
				except rest.ErrorResponse:
					pass
		else:
			dropbox_client.put_file(folder + "/" + os.path.basename(filename), f, overwrite=True)

if __name__=="__main__":
	backup_to_dropbox()