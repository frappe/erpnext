# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import validate_email_add
from frappe import _
from email.utils import parseaddr

class NewsletterList(Document):
	def onload(self):
		singles = [d.name for d in frappe.db.get_all("DocType", "name", {"issingle": 1})]
		self.get("__onload").import_types = [{"value": d.parent, "label": "{0} ({1})".format(d.parent, d.label)} \
			for d in frappe.db.get_all("DocField", ("parent", "label"), {"options": "Email"}) if d.parent not in singles]

	def import_from(self, doctype):
		"""Extract email ids from given doctype and add them to the current list"""
		meta = frappe.get_meta(doctype)
		email_field = [d.fieldname for d in meta.fields if d.fieldtype in ("Data", "Small Text") and d.options=="Email"][0]
		unsubscribed_field = "unsubscribed" if meta.get_field("unsubscribed") else None
		added = 0

		for user in frappe.db.get_all(doctype, [email_field, unsubscribed_field or "name"]):
			try:
				email = parseaddr(user.get(email_field))[1]
				if email:
					frappe.get_doc({
						"doctype": "Newsletter List Subscriber",
						"newsletter_list": self.name,
						"email": email,
						"unsubscribed": user.get(unsubscribed_field) if unsubscribed_field else 0
					}).insert(ignore_permissions=True)

					added += 1
			except Exception, e:
				# already added, ignore
				if e.args[0]!=1062:
					raise

		frappe.msgprint(_("{0} subscribers added").format(added))

		return self.update_total_subscribers()

	def update_total_subscribers(self):
		self.total_subscribers = self.get_total_subscribers()
		self.db_update()
		return self.total_subscribers

	def get_total_subscribers(self):
		return frappe.db.sql("""select count(*) from `tabNewsletter List Subscriber`
			where newsletter_list=%s""", self.name)[0][0]

	def on_trash(self):
		for d in frappe.get_all("Newsletter List Subscriber", "name", {"newsletter_list": self.name}):
			frappe.delete_doc("Newsletter List Subscriber", d.name)

@frappe.whitelist()
def import_from(name, doctype):
	nlist = frappe.get_doc("Newsletter List", name)
	if nlist.has_permission("write"):
		return nlist.import_from(doctype)

@frappe.whitelist()
def add_subscribers(name, email_list):
	if not isinstance(email_list, (list, tuple)):
		email_list = email_list.replace(",", "\n").split("\n")
	count = 0
	for email in email_list:
		email = email.strip()
		validate_email_add(email, True)

		if email:
			if not frappe.db.get_value("Newsletter List Subscriber",
				{"newsletter_list": name, "email": email}):
				frappe.get_doc({
					"doctype": "Newsletter List Subscriber",
					"newsletter_list": name,
					"email": email
				}).insert(ignore_permissions = frappe.flags.ignore_permissions)

				count += 1
			else:
				pass

	frappe.msgprint(_("{0} subscribers added").format(count))

	return frappe.get_doc("Newsletter List", name).update_total_subscribers()
