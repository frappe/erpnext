# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class ShareTransfer(Document):
	def validate(self):
		self.basic_validations()
		if self.transfer_type != 'Issue':
			self.validate_share_exist()

	def basic_validations(self):
		if self.transfer_type == 'Purchase':
			self.to_shareholder = ''
			if self.from_shareholder is None:
				frappe.throw('The field \'From Shareholder\' cannot be blank')
		elif (self.transfer_type == 'Issue'):
			self.from_shareholder = ''
			if self.to_shareholder is None:
				frappe.throw('The field \'To Shareholder\' cannot be blank')
		else:
			if self.from_shareholder is None:
				frappe.throw('The fields \'From Shareholder\' and \'To Shareholder\' cannot be blank')
		if self.from_shareholder == self.to_shareholder:
			frappe.throw('The seller and the buyer cannot be the same')
		if self.amount is None:
			self.amount = self.rate * self.no_of_shares
		if self.amount != self.rate * self.no_of_shares:
			frappe.throw('There\'s inconsistency between the rate, no of shares and the amount calculated')
		total_no_of_shares = 0
		if len(self.shares) != 0:
			for index, share in enumerate(self.shares):
				if share.from_no > share.to_no:
					frappe.throw('The starting share number cannot be greater than the ending share number for line {0}'.format(index+1))
				total_no_of_shares += share.to_no - share.from_no + 1 
			if total_no_of_shares != self.no_of_shares:
				frappe.throw('There\'s inconsistency between the total no. of shares and the share numbers')

	def validate_share_exist(self):
		if not self.share_exists():
			frappe.throw('The shareholder {0} doesn\'t own these shares'.format(self.from_name))

	def share_exists(self):
		# Go through all share transfers and check if the Shareholder has these shares to give away
		# return True if he has them
		# else return False
		docs = frappe.get_all('Share Transfer',
			or_filters = [
				['Share Transfer', 'from_shareholder', '=', self.from_shareholder],
				['Share Transfer', 'to_shareholder', '=', self.from_shareholder]
			],
			filters    = [
				['Share Transfer', 'company', '=', self.company],
				['Share Transfer', 'date', '<=', self.date],
				['Share Transfer', 'share_type', '=', self.share_type]
			],
			fields     = [
				'no_of_shares', 'from_shareholder', 'to_shareholder'
			]
		)

		shares = 0
		for doc in docs:
			if doc.from_shareholder == self.from_shareholder:
				shares -= doc.no_of_shares
			elif doc.to_shareholder == self.from_shareholder:
				shares += doc.no_of_shares

		if shares >= self.no_of_shares:
			return True
		else:
			return False

