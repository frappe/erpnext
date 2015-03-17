import frappe

def execute():
	frappe.reload_doc("email", "doctype", "email_account")

	# outgoing
	outgoing = dict(frappe.db.sql("select field, value from tabSingles where doctype='Outgoing Email Settings'"))
	if outgoing and outgoing['mail_server']:
		account = frappe.new_doc("Email Account")
		mapping = {
			"email_id": "mail_login",
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
		account.is_global = 1

		account.insert()

	# support
	support = dict(frappe.db.sql("select field, value from tabSingles where doctype='Support Email Settings'"))
	if support and support['mail_server']:
		account = frappe.new_doc("Email Account")
		mapping = {
			"enable_incoming": "sync_support_mails",
			"email_id": "mail_login",
			"password": "mail_password",
			"pop3_server": "mail_server",
			"use_ssl": "use_ssl",
			"signature": "support_signature",
			"enable_auto_reply": "send_autoreply",
			"auto_reply_message": "support_autoreply"
		}

		for target_fieldname, source_fieldname in mapping.iteritems():
			account.set(target_fieldname, support.get(source_fieldname))

		account.enable_outgoing = 0
		account.is_global = 1

		account.insert()

	# sales, jobs
	for doctype in ("Sales Email Settings", "Jobs Email Settings"):
		source = dict(frappe.db.sql("select field, value from tabSingles where doctype=%s", doctype))
		if source and  source.get('host'):
			account = frappe.new_doc("Email Account")
			mapping = {
				"enable_incoming": "extract_emails",
				"email_id": "username",
				"password": "password",
				"pop3_server": "host",
				"use_ssl": "use_ssl",
			}

			for target_fieldname, source_fieldname in mapping.iteritems():
				account.set(target_fieldname, source.get(source_fieldname))

			account.enable_outgoing = 0
			account.is_global = 1
			account.append_to = "Lead" if doctype=="Sales Email Settings" else "Job Applicant"

			account.insert()

	for doctype in ("Outgoing Email Settings", "Support Email Settings",
		"Sales Email Settings", "Jobs Email Settings"):
		frappe.delete_doc("DocType", doctype)

