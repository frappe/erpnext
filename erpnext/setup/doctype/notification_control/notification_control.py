# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe import _

from frappe.model.document import Document

class NotificationControl(Document):
	def get_message(self, arg):
		fn = arg.lower().replace(' ', '_') + '_message'
		v = frappe.db.sql("select value from tabSingles where field=%s and doctype=%s", (fn, 'Notification Control'))
		return v and v[0][0] or ''

	def set_message(self, arg = ''):
		fn = self.select_transaction.lower().replace(' ', '_') + '_message'
		frappe.db.set(self, fn, self.custom_message)
		frappe.msgprint(_("Message updated"))

