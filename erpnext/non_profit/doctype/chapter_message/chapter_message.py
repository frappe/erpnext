# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class ChapterMessage(Document):
	def validate(self):
		chapter = frappe.get_doc('Chapter', self.chapter)
		if frappe.session.user != chapter.chapter_head:
			frappe.throw(_('You are not athourized to send message for this Chapter.'))

	def on_update(self):
		chapter = frappe.get_doc('Chapter', self.chapter)
		recipients = [d.user for d in chapter.members]

		frappe.sendmail(recipients = recipients,
				sender=frappe.session.user,
				subject = self.subject,
				message = self.message,
				reference_doctype=chapter.doctype,
				reference_name=chapter.name
				)


		frappe.msgprint(_("Invitation Sent"))

