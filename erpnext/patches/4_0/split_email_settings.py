# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("core", "doctype", "outgoing_email_settings")
	frappe.reload_doc("support", "doctype", "support_email_settings")
	
	email_settings = frappe.get_doc("Email Settings")
	map_outgoing_email_settings(email_settings)
	map_support_email_settings(email_settings)
	frappe.delete_doc("Doctype", "Email Settings")
	
def map_outgoing_email_settings(email_settings):
	outgoing_email_settings = frappe.get_doc("Outgoing Email Settings")
	for fieldname in (("outgoing_mail_server", "mail_server"), 
		"use_ssl", "mail_port", "mail_login", "mail_password",
		"always_use_login_id_as_sender",
		"auto_email_id", "send_print_in_body_and_attachment"):

		if isinstance(fieldname, tuple):
			from_fieldname, to_fieldname = fieldname
		else:
			from_fieldname = to_fieldname = fieldname

		outgoing_email_settings.set(to_fieldname, email_settings.get(from_fieldname))

	outgoing_email_settings.save()
	
def map_support_email_settings(email_settings):
	support_email_settings = frappe.get_doc("Support Email Settings")
	
	for fieldname in ("sync_support_mails", "support_email", 
		("support_host", "mail_server"), 
		("support_use_ssl", "use_ssl"), 
		("support_username", "mail_login"), 
		("support_password", "mail_password"), 
		"support_signature", "send_autoreply", "support_autoreply"):
		
		if isinstance(fieldname, tuple):
			from_fieldname, to_fieldname = fieldname
		else:
			from_fieldname = to_fieldname = fieldname
	
		support_email_settings.set(to_fieldname, email_settings.get(from_fieldname))
	
	support_email_settings.save()
	
