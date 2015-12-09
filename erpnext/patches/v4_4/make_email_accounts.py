import frappe
from frappe.model import default_fields

def execute():
	frappe.reload_doc("email", "doctype", "email_account")

	# outgoing
	outgoing = dict(frappe.db.sql("select field, value from tabSingles where doctype='Outgoing Email Settings'"))
	if outgoing and outgoing['mail_server'] and outgoing['mail_login']:
		account = frappe.new_doc("Email Account")
		mapping = {
			"login_id_is_different": 1,
			"email_id": "auto_email_id",
			"login_id": "mail_login",
			"password": "mail_password",
			"footer": "footer",
			"smtp_server": "mail_server",
			"smtp_port": "mail_port",
			"use_tls": "use_ssl"
		}

		for target_fieldname, source_fieldname in mapping.iteritems():
			account.set(target_fieldname, outgoing.get(source_fieldname))

		account.enable_outgoing = 1
		account.enable_incoming = 0

		account.insert()

	# support
	support = dict(frappe.db.sql("select field, value from tabSingles where doctype='Support Email Settings'"))
	if support and support['mail_server'] and support['mail_login']:
		account = frappe.new_doc("Email Account")
		mapping = {
			"enable_incoming": "sync_support_mails",
			"email_id": "mail_login",
			"password": "mail_password",
			"email_server": "mail_server",
			"use_ssl": "use_ssl",
			"signature": "support_signature",
			"enable_auto_reply": "send_autoreply",
			"auto_reply_message": "support_autoreply"
		}

		for target_fieldname, source_fieldname in mapping.iteritems():
			account.set(target_fieldname, support.get(source_fieldname))

		account.enable_outgoing = 0
		account.append_to = "Issue"

		insert_or_update(account)

	# sales, jobs
	for doctype in ("Sales Email Settings", "Jobs Email Settings"):
		source = dict(frappe.db.sql("select field, value from tabSingles where doctype=%s", doctype))
		if source and  source.get('host') and source.get('username'):
			account = frappe.new_doc("Email Account")
			mapping = {
				"enable_incoming": "extract_emails",
				"email_id": "username",
				"password": "password",
				"email_server": "host",
				"use_ssl": "use_ssl",
			}

			for target_fieldname, source_fieldname in mapping.iteritems():
				account.set(target_fieldname, source.get(source_fieldname))

			account.enable_outgoing = 0
			account.append_to = "Lead" if doctype=="Sales Email Settings" else "Job Applicant"

			insert_or_update(account)

	for doctype in ("Outgoing Email Settings", "Support Email Settings",
		"Sales Email Settings", "Jobs Email Settings"):
		frappe.delete_doc("DocType", doctype)

def insert_or_update(account):
	try:
		account.insert()
	except frappe.NameError, e:
		if e.args[0]=="Email Account":
			existing_account = frappe.get_doc("Email Account", e.args[1])
			for key, value in account.as_dict().items():
				if not existing_account.get(key) and value \
					and key not in default_fields \
					and key != "__islocal":
					existing_account.set(key, value)

			existing_account.save()
		else:
			raise

