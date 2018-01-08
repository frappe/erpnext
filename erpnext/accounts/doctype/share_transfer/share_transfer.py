# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class ShareTransfer(Document):
	def validate(self):
		self.basic_validations()
		self.folio_no_validation()
		if self.transfer_type != 'Issue':
			self.validate_share_exist()

	def basic_validations(self):
		if self.transfer_type == 'Purchase':
			self.to_party = ''
			if self.from_party is None or self.from_party is '':
				frappe.throw('The field \'From Shareholder Party\' cannot be blank')
			if self.from_folio_no is None or self.from_folio_no is '':
				frappe.throw('The field \'From folio no\' cannot be blank')
		elif (self.transfer_type == 'Issue'):
			self.from_party = ''
			if self.to_party is None or self.to_party == '':
				frappe.throw('The field \'To Shareholder Party\' cannot be blank')
			if self.to_folio_no is None or self.from_folio_no is '':
				frappe.throw('The field \'To folio no\' cannot be blank')
		else:
			if self.from_party is None or self.to_party is None:
				frappe.throw('The fields \'From Shareholder\' and \'To Shareholder\' cannot be blank')
		if self.from_party == self.to_party:
			frappe.throw('The seller and the buyer cannot be the same')
		if self.amount is None:
			self.amount = self.rate * self.no_of_shares
		if self.amount != self.rate * self.no_of_shares:
			frappe.throw('There\'s inconsistency between the rate, no of shares and the amount calculated')
		total_no_of_shares = 0
		# if len(self.shares) != 0:
		# 	for index, share in enumerate(self.shares):
		# 		if share.from_no > share.to_no:
		# 			frappe.throw('The starting share number cannot be greater than the ending share number for line {0}'.format(index+1))
		# 		total_no_of_shares += share.to_no - share.from_no + 1
		# 	if total_no_of_shares != self.no_of_shares:
		# 		frappe.throw('There\'s inconsistency between the total no. of shares and the share numbers')

	def validate_share_exist(self):
		if not self.share_exists():
			frappe.throw('The shareholder party, {0} doesn\'t own these shares'.format(self.from_party))

	def share_exists(self):
		# Go through all share transfers and check if the Shareholder has these shares to give away
		# return True if he has them
		# else return False
		docs = frappe.get_all('Share Transfer',
			or_filters = [
				['Share Transfer', 'from_party', '=', self.from_party],
				['Share Transfer', 'to_party', '=', self.from_party]
			],
			filters    = [
				['Share Transfer', 'company', '=', self.company],
				['Share Transfer', 'date', '<=', self.date],
				['Share Transfer', 'share_type', '=', self.share_type]
			],
			fields     = [
				'no_of_shares', 'from_party', 'to_party'
			]
		)

		shares = 0
		for doc in docs:
			if doc.from_party == self.from_party:
				shares -= doc.no_of_shares
			elif doc.to_party == self.from_party:
				shares += doc.no_of_shares

		if shares >= self.no_of_shares:
			return True
		else:
			return False

	def folio_no_validation(self):
		parties = ['from_party', 'to_party']
		parties = [party for party in parties if self.get(party) is not '']
		for party in parties:
			doc = frappe.get_doc('Shareholder Party', self.get(party))
			if doc.company != self.company:
				frape.throw('The shareholder party doesn\'t belong to this company')
			if doc.folio_no is '' or doc.folio_no is None:
				doc.folio_no = self.from_folio_no if (party == 'from_party') else self.to_folio_no;
				doc.save()
			else:
				if doc.folio_no != self.from_folio_no if (party == 'from_party') else self.to_folio_no:
					frappe.throw('The folio numbers are not matching')