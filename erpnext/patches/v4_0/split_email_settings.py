# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	print "WARNING!!!! Email Settings not migrated. Please setup your email again."

	# this will happen if you are migrating very old accounts
	# comment out this line below and remember to create new Email Accounts
	# for incoming and outgoing mails
	raise Exception

	return


	frappe.reload_doc("core", "doctype", "outgoing_email_settings")
	frappe.reload_doc("support", "doctype", "support_email_settings")

	email_settings = get_email_settings()
	map_outgoing_email_settings(email_settings)
	map_support_email_settings(email_settings)


def map_outgoing_email_settings(email_settings):
	outgoing_email_settings = frappe.get_doc("Outgoing Email Settings")
	for fieldname in (("outgoing_mail_server", "mail_server"),
		"use_ssl", "mail_port", "mail_login", "mail_password",
		"always_use_login_id_as_sender", "auto_email_id"):

		if isinstance(fieldname, tuple):
			from_fieldname, to_fieldname = fieldname
		else:
			from_fieldname = to_fieldname = fieldname

		outgoing_email_settings.set(to_fieldname, email_settings.get(from_fieldname))

	outgoing_email_settings._fix_numeric_types()
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

	support_email_settings._fix_numeric_types()
	support_email_settings.save()

def get_email_settings():
	ret = {}
	for field, value in frappe.db.sql("select field, value from tabSingles where doctype='Email Settings'"):
		ret[field] = value
	return ret

