# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.exceptions import ValidationError
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import nowdate


class ShareDontExists(ValidationError): pass

class ShareTransfer(Document):
	def on_submit(self):
		if self.transfer_type == 'Issue':
			shareholder = self.get_company_shareholder()
			shareholder.append('share_balance', {
				'share_type': self.share_type,
				'from_no': self.from_no,
				'to_no': self.to_no,
				'rate': self.rate,
				'amount': self.amount,
				'no_of_shares': self.no_of_shares,
				'is_company': 1,
				'current_state': 'Issued'
			})
			shareholder.save()

			doc = self.get_shareholder_doc(self.to_shareholder)
			doc.append('share_balance', {
				'share_type': self.share_type,
				'from_no': self.from_no,
				'to_no': self.to_no,
				'rate': self.rate,
				'amount': self.amount,
				'no_of_shares': self.no_of_shares
			})
			doc.save()

		elif self.transfer_type == 'Purchase':
			self.remove_shares(self.from_shareholder)
			self.remove_shares(self.get_company_shareholder().name)

		elif self.transfer_type == 'Transfer':
			self.remove_shares(self.from_shareholder)
			doc = self.get_shareholder_doc(self.to_shareholder)
			doc.append('share_balance', {
				'share_type': self.share_type,
				'from_no': self.from_no,
				'to_no': self.to_no,
				'rate': self.rate,
				'amount': self.amount,
				'no_of_shares': self.no_of_shares
			})
			doc.save()

	def on_cancel(self):
		if self.transfer_type == 'Issue':
			compnay_shareholder = self.get_company_shareholder()
			self.remove_shares(compnay_shareholder.name)
			self.remove_shares(self.to_shareholder)

		elif self.transfer_type == 'Purchase':
			compnay_shareholder = self.get_company_shareholder()
			from_shareholder = self.get_shareholder_doc(self.from_shareholder)

			from_shareholder.append('share_balance', {
				'share_type': self.share_type,
				'from_no': self.from_no,
				'to_no': self.to_no,
				'rate': self.rate,
				'amount': self.amount,
				'no_of_shares': self.no_of_shares
			})

			from_shareholder.save()

			compnay_shareholder.append('share_balance', {
				'share_type': self.share_type,
				'from_no': self.from_no,
				'to_no': self.to_no,
				'rate': self.rate,
				'amount': self.amount,
				'no_of_shares': self.no_of_shares
			})

			compnay_shareholder.save()

		elif self.transfer_type == 'Transfer':
			self.remove_shares(self.to_shareholder)
			from_shareholder = self.get_shareholder_doc(self.from_shareholder)
			from_shareholder.append('share_balance', {
				'share_type': self.share_type,
				'from_no': self.from_no,
				'to_no': self.to_no,
				'rate': self.rate,
				'amount': self.amount,
				'no_of_shares': self.no_of_shares
			})
			from_shareholder.save()

	def validate(self):
		self.get_company_shareholder()
		self.basic_validations()
		self.folio_no_validation()

		if self.transfer_type == 'Issue':
			# validate share doesn't exist in company
			ret_val = self.share_exists(self.get_company_shareholder().name)
			if ret_val in ('Complete', 'Partial'):
				frappe.throw(_('The shares already exist'), frappe.DuplicateEntryError)
		else:
			# validate share exists with from_shareholder
			ret_val = self.share_exists(self.from_shareholder)
			if ret_val in ('Outside', 'Partial'):
				frappe.throw(_("The shares don't exist with the {0}")
					.format(self.from_shareholder), ShareDontExists)

	def basic_validations(self):
		if self.transfer_type == 'Purchase':
			self.to_shareholder = ''
			if not self.from_shareholder:
				frappe.throw(_('The field From Shareholder cannot be blank'))
			if not self.from_folio_no:
				self.to_folio_no = self.autoname_folio(self.to_shareholder)
			if not self.asset_account:
				frappe.throw(_('The field Asset Account cannot be blank'))
		elif (self.transfer_type == 'Issue'):
			self.from_shareholder = ''
			if not self.to_shareholder:
				frappe.throw(_('The field To Shareholder cannot be blank'))
			if not self.to_folio_no:
				self.to_folio_no = self.autoname_folio(self.to_shareholder)
			if not self.asset_account:
				frappe.throw(_('The field Asset Account cannot be blank'))
		else:
			if not self.from_shareholder or not self.to_shareholder:
				frappe.throw(_('The fields From Shareholder and To Shareholder cannot be blank'))
			if not self.to_folio_no:
				self.to_folio_no = self.autoname_folio(self.to_shareholder)
		if not self.equity_or_liability_account:
				frappe.throw(_('The field Equity/Liability Account cannot be blank'))
		if self.from_shareholder == self.to_shareholder:
			frappe.throw(_('The seller and the buyer cannot be the same'))
		if self.no_of_shares != self.to_no - self.from_no + 1:
			frappe.throw(_('The number of shares and the share numbers are inconsistent'))
		if not self.amount:
			self.amount = self.rate * self.no_of_shares
		if self.amount != self.rate * self.no_of_shares:
			frappe.throw(_('There are inconsistencies between the rate, no of shares and the amount calculated'))

	def share_exists(self, shareholder):
		doc = self.get_shareholder_doc(shareholder)
		for entry in doc.share_balance:
			if entry.share_type != self.share_type or \
				entry.from_no > self.to_no or \
				entry.to_no < self.from_no:
				continue # since query lies outside bounds
			elif entry.from_no <= self.from_no and entry.to_no >= self.to_no: #both inside
				return 'Complete' # absolute truth!
			elif entry.from_no <= self.from_no <= self.to_no:
				return 'Partial'
			elif entry.from_no <= self.to_no <= entry.to_no:
				return 'Partial'

		return 'Outside'

	def folio_no_validation(self):
		shareholder_fields = ['from_shareholder', 'to_shareholder']
		for shareholder_field in shareholder_fields:
			shareholder_name = self.get(shareholder_field)
			if not shareholder_name:
				continue
			doc = self.get_shareholder_doc(shareholder_name)
			if doc.company != self.company:
				frappe.throw(_('The shareholder does not belong to this company'))
			if not doc.folio_no:
				doc.folio_no = self.from_folio_no \
					if (shareholder_field == 'from_shareholder') else self.to_folio_no
				doc.save()
			else:
				if doc.folio_no and doc.folio_no != (self.from_folio_no if (shareholder_field == 'from_shareholder') else self.to_folio_no):
					frappe.throw(_('The folio numbers are not matching'))

	def autoname_folio(self, shareholder, is_company=False):
		if is_company:
			doc = self.get_company_shareholder()
		else:
			doc = self.get_shareholder_doc(shareholder)
		doc.folio_no = make_autoname('FN.#####')
		doc.save()
		return doc.folio_no

	def remove_shares(self, shareholder):
		# query = {'from_no': share_starting_no, 'to_no': share_ending_no}
		# Shares exist for sure
		# Iterate over all entries and modify entry if in entry
		doc = frappe.get_doc('Shareholder', shareholder)
		current_entries = doc.share_balance
		new_entries = []

		for entry in current_entries:
			# use spaceage logic here
			if entry.share_type != self.share_type or \
				entry.from_no > self.to_no or \
				entry.to_no < self.from_no:
				new_entries.append(entry)
				continue # since query lies outside bounds
			elif entry.from_no <= self.from_no and entry.to_no >= self.to_no:
				#split
				if entry.from_no == self.from_no:
					if entry.to_no == self.to_no:
						pass #nothing to append
					else:
						new_entries.append(self.return_share_balance_entry(self.to_no+1, entry.to_no, entry.rate))
				else:
					if entry.to_no == self.to_no:
						new_entries.append(self.return_share_balance_entry(entry.from_no, self.from_no-1, entry.rate))
					else:
						new_entries.append(self.return_share_balance_entry(entry.from_no, self.from_no-1, entry.rate))
						new_entries.append(self.return_share_balance_entry(self.to_no+1, entry.to_no, entry.rate))
			elif entry.from_no >= self.from_no and entry.to_no <= self.to_no:
				# split and check
				pass #nothing to append
			elif self.from_no <= entry.from_no <= self.to_no and entry.to_no >= self.to_no:
				new_entries.append(self.return_share_balance_entry(self.to_no+1, entry.to_no, entry.rate))
			elif self.from_no <= entry.to_no <= self.to_no and entry.from_no <= self.from_no:
				new_entries.append(self.return_share_balance_entry(entry.from_no, self.from_no-1, entry.rate))
			else:
				new_entries.append(entry)

		doc.share_balance = []
		for entry in new_entries:
			doc.append('share_balance', entry)
		doc.save()

	def return_share_balance_entry(self, from_no, to_no, rate):
		# return an entry as a dict
		return {
			'share_type'   : self.share_type,
			'from_no'	   : from_no,
			'to_no'		   : to_no,
			'rate'		   : rate,
			'amount'	   : self.rate * (to_no - from_no + 1),
			'no_of_shares' : to_no - from_no + 1
		}

	def get_shareholder_doc(self, shareholder):
		# Get Shareholder doc based on the Shareholder name
		if shareholder:
			query_filters = {'name': shareholder}

		name = frappe.db.get_value('Shareholder', {'name': shareholder}, 'name')

		return frappe.get_doc('Shareholder', name)

	def get_company_shareholder(self):
		# Get company doc or create one if not present
		company_shareholder = frappe.db.get_value('Shareholder',
			{
				'company': self.company,
				'is_company': 1
			}, 'name')

		if company_shareholder:
			return frappe.get_doc('Shareholder', company_shareholder)
		else:
			shareholder = frappe.get_doc({
					'doctype': 'Shareholder',
					'title': self.company,
					'company': self.company,
					'is_company': 1
				})
			shareholder.insert()

			return shareholder

@frappe.whitelist()
def make_jv_entry( company, account, amount, payment_account,\
	credit_applicant_type, credit_applicant, debit_applicant_type, debit_applicant):
	journal_entry = frappe.new_doc('Journal Entry')
	journal_entry.voucher_type = 'Journal Entry'
	journal_entry.company = company
	journal_entry.posting_date = nowdate()
	account_amt_list = []

	account_amt_list.append({
		"account": account,
		"debit_in_account_currency": amount,
		"party_type": debit_applicant_type,
		"party": debit_applicant,
		})
	account_amt_list.append({
		"account": payment_account,
		"credit_in_account_currency": amount,
		"party_type": credit_applicant_type,
		"party": credit_applicant,
		})
	journal_entry.set("accounts", account_amt_list)
	return journal_entry.as_dict()
