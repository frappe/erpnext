# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class ShortcutSettings(Document):
	def on_update(self):
		frappe.publish_realtime('update_shortcut_setting', self, user=self.user, after_commit=True)
	def after_insert(self):
		frappe.publish_realtime('update_shortcut_setting', self, user=self.user, after_commit=True)

def has_permission(doc, user):
	return doc.user == user

def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	return "(`tabShortcut Settings`.`user`='{user}')".format(user=user)