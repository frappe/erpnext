# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils.scheduler import log

def send_newsletter(newsletter):
	try:
		doc = frappe.get_doc("Newsletter", newsletter)
		doc.send_bulk()

	except:
		frappe.db.rollback()

		# wasn't able to send emails :(
		doc.db_set("email_sent", 0)
		frappe.db.commit()

		log("send_newsletter")

		raise

	else:
		frappe.db.commit()
