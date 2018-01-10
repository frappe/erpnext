# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.naming   import make_autoname

class ShareTransfer(Document):
	def before_save(self):
		if self.transfer_type == 'Issue':
			#todo make entry in company party
			company_party_doc = frappe.get_doc('Shareholder Party', self.company)
			company_party_doc.append('share_balance', {
				'share_type': self.share_type,
				'from_no': self.from_no,
				'to_no': self.to_no,
				'rate': self.rate,
				'amount': self.amount,
				'no_of_shares': self.no_of_shares,
				'is_company': 1,
				'current_state': 'Issued'
			})
			company_party_doc.save()
			#todo add an entry in the required Shareholder Party's Share Balance
			doc = frappe.get_doc('Shareholder Party', self.to_party)
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
			#todo remove the necessary entry from the required Shareholder Party's Share Balance
			self.remove_shares(self.from_party)
			#todo edit in company party
			self.remove_shares(self.company, is_company=1)
		elif self.transfer_type == 'Transfer':
			#todo remove the necessary entries from the from Shareholder Party's Share Balance
			self.remove_shares(self.from_party)
			#todo add an entry in the to Shareholder Party's Share Balance
			doc = frappe.get_doc('Shareholder Party', self.to_party)
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
			#todo if 1st make a Shareholder Party under Company Name
			if not frappe.db.exists('Shareholder Party', self.company):
				company_party_doc = frappe.get_doc({
					'doctype': 'Shareholder Party',
					'title': self.company,
					'company': self.company,
					'is_company': 1 
				})
				company_party_doc.insert()
			# validate share doesnt exist in company
			ret_val = self.share_exists(self.company)
			if ret_val != False:
				frappe.throw('The shares already exist')
		else:
			# validate share exists with from_party 
			ret_val = self.share_exists(self.from_party)
			if ret_val != True:
				frappe.throw('The shares don\'t exist with the {0}'.format(self.from_party))

	def basic_validations(self):
		if self.transfer_type == 'Purchase':
			self.to_party = ''
			if self.from_party is None or self.from_party is '':
				frappe.throw('The field \'From Shareholder Party\' cannot be blank')
			if self.from_folio_no is None or self.from_folio_no is '':
				self.to_folio_no = self.autoname_folio(self.to_party)
		elif (self.transfer_type == 'Issue'):
			self.from_party = ''
			if self.to_party is None or self.to_party == '':
				frappe.throw('The field \'To Shareholder Party\' cannot be blank')
			if self.to_folio_no is None or self.to_folio_no is '':
				self.to_folio_no = self.autoname_folio(self.to_party)
		else:
			if self.from_party is None or self.to_party is None:
				frappe.throw('The fields \'From Shareholder\' and \'To Shareholder\' cannot be blank')
		if self.from_party == self.to_party:
			frappe.throw('The seller and the buyer cannot be the same')
		if self.no_of_shares != self.to_no - self.from_no + 1:
			frappe.throw('The number of shares and the share numbers are inconsistent!') 
		if self.amount is None:
			self.amount = self.rate * self.no_of_shares
		if self.amount != self.rate * self.no_of_shares:
			frappe.throw('There\'s inconsistency between the rate, no of shares and the amount calculated')
		total_no_of_shares = 0

	def share_exists(self, party):
		# return True				if exits,
		# 		 False	 			if completely doesn't exist,
		#		 'partially exists' if partailly doesn't exist
		ret_val = self.recursive_share_check(party, self.share_type,
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

	def recursive_share_check(self, party, share_type, query):
		# query = {'from_no': share_starting_no, 'to_no': share_ending_no}
		# Recursive check if a given part of shares is held by the party
		# return a list containing True and False
		# Eg. [True, False, True]
		# All True  implies its completely inside
		# All False implies its completely outside
		# A   mix   implies its partially  inside/outside
		does_share_exist = []
		doc = frappe.get_doc('Shareholder Party', party)
		for entry in doc.share_balance:
			if entry.share_type != share_type or \
				entry.from_no > query['to_no'] or \
				entry.to_no < query['from_no']:
				continue # since query lies outside bounds
			elif entry.from_no <= query['from_no'] and entry.to_no >= query['to_no']:
				return [True] # absolute truth!
			elif entry.from_no >= query['from_no'] and entry.to_no <= query['to_no']:
				# split and check
				does_share_exist.extend(self.recursive_share_check(party,
					share_type,
					{
						'from_no': query['from_no'],
						'to_no': entry.from_no - 1
					}
				))
				does_share_exist.append(True)
				does_share_exist.extend(self.recursive_share_check(party,
					share_type,
					{
						'from_no': entry.to_no + 1,
						'to_no': query['to_no']
					}
				))
			elif query['from_no'] <= entry.from_no <= query['to_no'] and entry.to_no >= query['to_no']:
				does_share_exist.extend(self.recursive_share_check(party,
					share_type,
					{
						'from_no': query['from_no'],
						'to_no': entry.from_no - 1
					}
				))
			elif query['from_no'] <= entry.to_no <= query['to_no'] and entry.from_no <= query['from_no']:
				does_share_exist.extend(self.recursive_share_check(party,
					share_type,
					{
						'from_no': entry.to_no + 1,
						'to_no': query['to_no']
					}
				))

		does_share_exist.append(False)
		return does_share_exist

	def folio_no_validation(self):
		parties = ['from_party', 'to_party']
		parties = [party for party in parties if self.get(party) is not '']
		for party in parties:
			doc = frappe.get_doc('Shareholder Party', self.get(party))
			if doc.company != self.company:
				frappe.throw('The shareholder party doesn\'t belong to this company')
			if doc.folio_no is '' or doc.folio_no is None:
				doc.folio_no = self.from_folio_no if (party == 'from_party') else self.to_folio_no;
				doc.save()
			else:
				if doc.folio_no != (self.from_folio_no if (party == 'from_party') else self.to_folio_no):
					frappe.throw('The folio numbers are not matching')

	def autoname_folio(self, party):
		doc = frappe.get_doc('Shareholder Party', party)
		doc.folio_no = make_autoname('FN.#####')
		doc.save()
		return doc.folio_no

	def remove_shares(self, party, is_company=0):
		self.iterative_share_removal(party, self.share_type,
			{
				'from_no': self.from_no,
				'to_no'  : self.to_no
			},
			rate       = self.rate,
			amount	   = self.amount,
			is_company = is_company
		)

	def iterative_share_removal(self, party, share_type, query, rate, amount, is_company=0):
		# query = {'from_no': share_starting_no, 'to_no': share_ending_no}
		# Shares exist for sure
		# Iterate over all entries and modify entry if in entry
		doc = frappe.get_doc('Shareholder Party', party)
		current_entries = doc.share_balance
		new_entries = []

		for entry in current_entries:
			# use spaceage logic here
			if entry.share_type != share_type or \
				entry.from_no > query['to_no'] or \
				entry.to_no < query['from_no']:
				continue # since query lies outside bounds
			elif entry.from_no <= query['from_no'] and entry.to_no >= query['to_no']:
				#split
				if entry.from_no == query['from_no']:
					if entry.to_no == query['to_no']:
						pass #nothing to append
					else:
						new_entries.append(self.return_share_balance_entry(query['to_no']+1, entry.to_no))
				else:
					if entry.to_no == query['to_no']:
						new_entries.append(self.return_share_balance_entry(entry.from_no, query['from_no']-1))
					else:
						new_entries.append(self.return_share_balance_entry(entry.from_no, query['from_no']-1))
						new_entries.append(self.return_share_balance_entry(query['to_no']+1, entry.to_no))
			elif entry.from_no >= query['from_no'] and entry.to_no <= query['to_no']:
				# split and check
				pass #nothing to append
			elif query['from_no'] <= entry.from_no <= query['to_no'] and entry.to_no >= query['to_no']:
				new_entries.append(self.return_share_balance_entry(query['to_no']+1, entry.to_no))
			elif query['from_no'] <= entry.to_no <= query['to_no'] and entry.from_no <= query['from_no']:
				new_entries.append(self.return_share_balance_entry(entry.from_no, query['from_no']-1))
			else:
				new_entries.append(entry)

		doc.share_balance = []
		for entry in new_entries:
			doc.append('share_balance', entry)
		doc.save()

	def return_share_balance_entry(self, from_no, to_no):
		# return an entry as a dict
		return {
			'share_type'   : self.share_type,
			'from_no'	   : from_no,
			'to_no'		   : to_no,
			'rate'		   : self.rate,
			'amount'	   : self.rate * (to_no - from_no + 1),
			'no_of_shares' : to_no - from_no + 1
		}