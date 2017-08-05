# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class PaymentDueDate(Document):
	def validate(self):
		self.validate_numerical_fields()
		self.validate_discount()

	def validate_numerical_fields(self):
		if cint(self.term_days) < 0:
			frappe.msgprint(
				_('Term Days field cannot be less than 0'),
				raise_exception=1, title='Error')

		if cint(self.discount_percentage) < 0:
			frappe.msgprint(
				_('Discount cannot be less than 0'),
				raise_exception=1, title='Error')

		if cint(self.discount_days) < 0:
			frappe.msgprint(
				_('Discount Days cannot be less than 0'),
				raise_exception=1, title='Error')

	def validate_discount(self):
		if self.with_discount:
			self.validate_discount_fields()
			self.validate_discount_days()

	def validate_discount_fields(self):
		if not self.discount_percentage or not self.discount_days:
			frappe.msgprint(
				_('When Include Cash Discount is checked, Discount Percentage and Discount Days are compulsory.'),
				raise_exception=1, title='Error')

	def validate_discount_days(self):
		if not self.term_days:
			frappe.msgprint(
				_('Term Days is compulsory if defining cash discount parameters.'),
				raise_exception=1, title='Error')

		if self.term_days < self.discount_days:
			frappe.msgprint(
				_('Discount Days should not be more than Term Days'),
				raise_exception=1, title='Error')