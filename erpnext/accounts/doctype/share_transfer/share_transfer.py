# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming   import make_autoname
from frappe.exceptions import ValidationError
from frappe.utils import nowdate

class ShareDontExists(ValidationError): pass

class ShareTransfer(Document):
	def before_submit(self):
		if self.transfer_type == 'Issue':
			shareholder = self.get_shareholder_doc(self.company)
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

			doc = frappe.get_doc('Shareholder', self.to_shareholder)
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
			self.remove_shares(self.get_shareholder_doc(self.company).name)

		elif self.transfer_type == 'Transfer':
			self.remove_shares(self.from_shareholder)
			doc = frappe.get_doc('Shareholder', self.to_shareholder)
			doc.append('share_balance', {
				'share_type': self.share_type,
				'from_no': self.from_no,
				'to_no': self.to_no,
				'rate': self.rate,
				'amount': self.amount,
				'no_of_shares': self.no_of_shares
			})
			doc.save()

	def validate(self):
		self.basic_validations()
		self.folio_no_validation()
		if self.transfer_type == 'Issue':
			if not self.get_shareholder_doc(self.company):
				shareholder = frappe.get_doc({
					'doctype': 'Shareholder',
					'title': self.company,
					'company': self.company,
					'is_company': 1
				})
				shareholder.insert()
			# validate share doesnt exist in company
			ret_val = self.share_exists(self.get_shareholder_doc(self.company).name)
			if ret_val != False:
				frappe.throw(_('The shares already exist'), frappe.DuplicateEntryError)
		else:
			# validate share exists with from_shareholder
			ret_val = self.share_exists(self.from_shareholder)
			if ret_val != True:
				frappe.throw(_("The shares don't exist with the {0}")
					.format(self.from_shareholder), ShareDontExists)

	def basic_validations(self):
		if self.transfer_type == 'Purchase':
			self.to_shareholder = ''
			if self.from_shareholder is None or self.from_shareholder is '':
				frappe.throw(_('The field From Shareholder cannot be blank'))
			if self.from_folio_no is None or self.from_folio_no is '':
				self.to_folio_no = self.autoname_folio(self.to_shareholder)
		elif (self.transfer_type == 'Issue'):
			self.from_shareholder = ''
			if self.to_shareholder is None or self.to_shareholder == '':
				frappe.throw(_('The field To Shareholder cannot be blank'))
			if self.to_folio_no is None or self.to_folio_no is '':
				self.to_folio_no = self.autoname_folio(self.to_shareholder)
		else:
			if self.from_shareholder is None or self.to_shareholder is None:
				frappe.throw(_('The fields From Shareholder and To Shareholder cannot be blank'))
			if self.to_folio_no is None or self.to_folio_no is '':
				self.to_folio_no = self.autoname_folio(self.to_shareholder)
		if self.from_shareholder == self.to_shareholder:
			frappe.throw(_('The seller and the buyer cannot be the same'))
		if self.no_of_shares != self.to_no - self.from_no + 1:
			frappe.throw(_('The number of shares and the share numbers are inconsistent'))
		if self.amount is None:
			self.amount = self.rate * self.no_of_shares
		if self.amount != self.rate * self.no_of_shares:
			frappe.throw(_('There are inconsistencies between the rate, no of shares and the amount calculated'))

	def share_exists(self, shareholder):
		# return True if exits,
		# False if completely doesn't exist,
		# 'partially exists' if partailly doesn't exist
		ret_val = self.recursive_share_check(shareholder, self.share_type,
			query = {
				'from_no': self.from_no,
				'to_no': self.to_no
			}
		)
		if all(boolean == True for boolean in ret_val):
			return True
		elif True in ret_val:
			return 'partially exists'
		else:
			return False

	def recursive_share_check(self, shareholder, share_type, query):
		# query = {'from_no': share_starting_no, 'to_no': share_ending_no}
		# Recursive check if a given part of shares is held by the shareholder
		# return a list containing True and False
		# Eg. [True, False, True]
		# All True  implies its completely inside
		# All False implies its completely outside
		# A   mix   implies its partially  inside/outside
		does_share_exist = []
		doc = frappe.get_doc('Shareholder', shareholder)
		for entry in doc.share_balance:
			if entry.share_type != share_type or \
				entry.from_no > query['to_no'] or \
				entry.to_no < query['from_no']:
				continue # since query lies outside bounds
			elif entry.from_no <= query['from_no'] and entry.to_no >= query['to_no']:
				return [True] # absolute truth!
			elif entry.from_no >= query['from_no'] and entry.to_no <= query['to_no']:
				# split and check
				does_share_exist.extend(self.recursive_share_check(shareholder,
					share_type,
					{
						'from_no': query['from_no'],
						'to_no': entry.from_no - 1
					}
				))
				does_share_exist.append(True)
				does_share_exist.extend(self.recursive_share_check(shareholder,
					share_type,
					{
						'from_no': entry.to_no + 1,
						'to_no': query['to_no']
					}
				))
			elif query['from_no'] <= entry.from_no <= query['to_no'] and entry.to_no >= query['to_no']:
				does_share_exist.extend(self.recursive_share_check(shareholder,
					share_type,
					{
						'from_no': query['from_no'],
						'to_no': entry.from_no - 1
					}
				))
			elif query['from_no'] <= entry.to_no <= query['to_no'] and entry.from_no <= query['from_no']:
				does_share_exist.extend(self.recursive_share_check(shareholder,
					share_type,
					{
						'from_no': entry.to_no + 1,
						'to_no': query['to_no']
					}
				))

		does_share_exist.append(False)
		return does_share_exist

	def folio_no_validation(self):
		shareholders = ['from_shareholder', 'to_shareholder']
		shareholders = [shareholder for shareholder in shareholders if self.get(shareholder) is not '']
		for shareholder in shareholders:
			doc = frappe.get_doc('Shareholder', self.get(shareholder))
			if doc.company != self.company:
				frappe.throw(_('The shareholder does not belong to this company'))
			if doc.folio_no is '' or doc.folio_no is None:
				doc.folio_no = self.from_folio_no \
					if (shareholder == 'from_shareholder') else self.to_folio_no;
				doc.save()
			else:
				if doc.folio_no != (self.from_folio_no if (shareholder == 'from_shareholder') else self.to_folio_no):
					frappe.throw(_('The folio numbers are not matching'))

	def autoname_folio(self, shareholder, is_company=False):
		if is_company:
			doc = self.get_shareholder_doc(shareholder)
		else:
			doc = frappe.get_doc('Shareholder' , shareholder)
		doc.folio_no = make_autoname('FN.#####')
		doc.save()
		return doc.folio_no

	def remove_shares(self, shareholder):
		self.iterative_share_removal(shareholder, self.share_type,
			{
				'from_no': self.from_no,
				'to_no'  : self.to_no
			},
			rate = self.rate,
			amount = self.amount
		)

	def iterative_share_removal(self, shareholder, share_type, query, rate, amount):
		# query = {'from_no': share_starting_no, 'to_no': share_ending_no}
		# Shares exist for sure
		# Iterate over all entries and modify entry if in entry
		doc = frappe.get_doc('Shareholder', shareholder)
		current_entries = doc.share_balance
		new_entries = []

		for entry in current_entries:
			# use spaceage logic here
			if entry.share_type != share_type or \
				entry.from_no > query['to_no'] or \
				entry.to_no < query['from_no']:
				new_entries.append(entry)
				continue # since query lies outside bounds
			elif entry.from_no <= query['from_no'] and entry.to_no >= query['to_no']:
				#split
				if entry.from_no == query['from_no']:
					if entry.to_no == query['to_no']:
						pass #nothing to append
					else:
						new_entries.append(self.return_share_balance_entry(query['to_no']+1, entry.to_no, entry.rate))
				else:
					if entry.to_no == query['to_no']:
						new_entries.append(self.return_share_balance_entry(entry.from_no, query['from_no']-1, entry.rate))
					else:
						new_entries.append(self.return_share_balance_entry(entry.from_no, query['from_no']-1, entry.rate))
						new_entries.append(self.return_share_balance_entry(query['to_no']+1, entry.to_no, entry.rate))
			elif entry.from_no >= query['from_no'] and entry.to_no <= query['to_no']:
				# split and check
				pass #nothing to append
			elif query['from_no'] <= entry.from_no <= query['to_no'] and entry.to_no >= query['to_no']:
				new_entries.append(self.return_share_balance_entry(query['to_no']+1, entry.to_no, entry.rate))
			elif query['from_no'] <= entry.to_no <= query['to_no'] and entry.from_no <= query['from_no']:
				new_entries.append(self.return_share_balance_entry(entry.from_no, query['from_no']-1, entry.rate))
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
		# Get Shareholder doc based on the Shareholder title
		doc = frappe.get_list('Shareholder',
			filters = [
				('Shareholder', 'title', '=', shareholder)
			]
		)
		if len(doc) == 1:
			return frappe.get_doc('Shareholder', doc[0]['name'])
		else: #It will necessarily by 0 indicating it doesn't exist
			return False

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