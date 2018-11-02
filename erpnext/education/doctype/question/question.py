# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Question(Document):

	def get_answer(self):
		options = self.get_all_children()
		answers = [item.name for item in options if item.is_correct == True]
		if len(answers) == 0:
			frappe.throw("No correct answer is set for {0}".format(self.name))
			return None
		elif len(answers) == 1:
			return answers[0]
		else:
			return answers