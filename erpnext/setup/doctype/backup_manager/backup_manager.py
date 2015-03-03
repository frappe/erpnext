# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

from frappe.model.document import Document

class BackupManager(Document):
	pass

def take_backups_daily():
	take_backups_if("Daily")

def take_backups_weekly():
	take_backups_if("Weekly")

def take_backups_if(freq):
	if frappe.db.get_value("Backup Manager", None, "upload_backups_to_dropbox")==freq:
		take_backups_dropbox()

	# if frappe.db.get_value("Backup Manager", None, "upload_backups_to_gdrive")==freq:
	# 	take_backups_gdrive()

@frappe.whitelist()
def take_backups_dropbox():
	did_not_upload, error_log = [], []
	try:
		from erpnext.setup.doctype.backup_manager.backup_dropbox import backup_to_dropbox
		did_not_upload, error_log = backup_to_dropbox()
		if did_not_upload: raise Exception

		send_email(True, "Dropbox")
	except Exception:
		file_and_error = [" - ".join(f) for f in zip(did_not_upload, error_log)]
		error_message = ("\n".join(file_and_error) + "\n" + frappe.get_traceback())
		frappe.errprint(error_message)
		send_email(False, "Dropbox", error_message)

#backup to gdrive
@frappe.whitelist()
def take_backups_gdrive():
	did_not_upload, error_log = [], []
	try:
		from erpnext.setup.doctype.backup_manager.backup_googledrive import backup_to_gdrive
		did_not_upload, error_log = backup_to_gdrive()
		if did_not_upload: raise Exception

		send_email(True, "Google Drive")
	except Exception:
		file_and_error = [" - ".join(f) for f in zip(did_not_upload, error_log)]
		error_message = ("\n".join(file_and_error) + "\n" + frappe.get_traceback())
		frappe.errprint(error_message)
		send_email(False, "Google Drive", error_message)

def send_email(success, service_name, error_status=None):
	if success:
		subject = "Backup Upload Successful"
		message ="""<h3>Backup Uploaded Successfully</h3><p>Hi there, this is just to inform you
		that your backup was successfully uploaded to your %s account. So relax!</p>
		""" % service_name

	else:
		subject = "[Warning] Backup Upload Failed"
		message ="""<h3>Backup Upload Failed</h3><p>Oops, your automated backup to %s
		failed.</p>
		<p>Error message: %s</p>
		<p>Please contact your system manager for more information.</p>
		""" % (service_name, error_status)

	if not frappe.db:
		frappe.connect()

	recipients = frappe.db.get_value("Backup Manager", None, "send_notifications_to").split(",")
	frappe.sendmail(recipients=recipients, subject=subject, message=message)
