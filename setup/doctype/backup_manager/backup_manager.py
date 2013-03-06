# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import _
from webnotes.utils import get_request_site_address

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl

@webnotes.whitelist()
def get_dropbox_authorize_url():
	from dropbox import session

	try:
		from conf import dropbox_access_key, dropbox_secret_key
	except ImportError, e:
		webnotes.msgprint(_("Please set Dropbox access keys in") + " conf.py", 
		raise_exception=True)
		
	sess = session.DropboxSession(dropbox_access_key, dropbox_secret_key, "app_folder")
	request_token = sess.obtain_request_token()
	return_address = get_request_site_address(True) \
		+ "?cmd=setup.doctype.backup_manager.backup_manager.dropbox_callback"
	
	url = sess.build_authorize_url(request_token, return_address)
		
	return {
		"url": url,
		"key": request_token.key,
		"secret": request_token.secret,
	}
	
@webnotes.whitelist(allow_guest=True)
def dropbox_callback(oauth_token=None, not_approved=False):
	if not not_approved:
		if webnotes.conn.get_value("Backup Manager", None, "dropbox_access_key")==oauth_token:		
			webnotes.conn.set_value("Backup Manager", "Backup Manager", "dropbox_access_allowed", 1)
			message = "Dropbox access allowed."
		else:
			webnotes.conn.set_value("Backup Manager", "Backup Manager", "dropbox_access_allowed", 0)
			message = "Illegal Access Token Please try again."
	else:
		webnotes.conn.set_value("Backup Manager", "Backup Manager", "dropbox_access_allowed", 0)
		message = "Dropbox Access not approved."
	
	webnotes.message_title = "Dropbox Approval"
	webnotes.message = "<h3>%s</h3><p>Please close this window.</p>" % message
		
	webnotes.conn.commit()
	webnotes.response['type'] = 'page'
	webnotes.response['page_name'] = 'message.html'
