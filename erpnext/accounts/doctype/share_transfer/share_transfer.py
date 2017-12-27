# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from operator import itemgetter
import copy

class ShareTransfer(Document):
	def validate(self):
		self.basic_validations()
		if self.transfer_type == 'Issue':
			self.validate_issue()
		elif self.transfer_type == 'Purchase':
			self.validate_purchase()
		else:
			self.validate_transfer()

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
		for index, share in enumerate(self.shares):
			if share.from_no > share.to_no:
				frappe.throw('The starting share number cannot be greater than the ending share number for line {0}'.format(index+1))
			total_no_of_shares += share.to_no - share.from_no + 1 
		if total_no_of_shares != self.no_of_shares:
			frappe.throw('There\'s inconsistency between the total no. of shares and the share numbers')

	def validate_issue(self):
		shareholder = self.share_exists_with()
		if shareholder:
			frappe.throw('These shares already exist with the shareholder {0}'.format(shareholder))
		else:
			self.add_shares()

	def validate_purchase(self):
		if self.share_exists_with(self.from_shareholder):
			self.remove_shares()
		else:
			frappe.throw('The shareholder {0} doesn\'t own these shares'.format(self.from_shareholder))

	def validate_transfer(self):
		if self.share_exists_with(self.from_shareholder):
			self.remove_shares()
			self.add_shares()
		else:
			frappe.throw('The shareholder {0} doesn\'t own these shares'.format(self.from_shareholder))

	def share_exists_with(self, shareholder_name=False):
		# If no arguments are passed, it'll go through all the shareholders and return the name
		# shareholder_name argument if passed will be to check if they exist with the passed shareholder
		# [ ] return name of person who share exists with
		# [ ] else return False
		if shareholder_name:
			shareholders = frappe.get_all('Shareholder', filters=[["total_amount", ">", 0], ["shareholder", "=", shareholder_name]])
		else:
			shareholders = frappe.get_all('Shareholder', filters=[["total_amount", ">", 0]])

		for shareholder in shareholders:
			shareholder_shares    = []
			share_transfer_shares = []
			shareholder = frappe.get_doc('Shareholder', shareholder.name)
			for ledger in shareholder.share_ledger:
				if ledger.company != self.company:
					continue
				shareholder_shares.append([ledger.from_no, ledger.to_no])
			for share in self.shares:
				share_transfer_shares.append([share.from_no, share.to_no])
			shareholder_shares    = sorted(shareholder_shares,    key=itemgetter(0))			
			share_transfer_shares = sorted(share_transfer_shares, key=itemgetter(0))
			
			if self.recursive_test(shareholder_shares, share_transfer_shares):
				if shareholder_name:
					return True
				else:
					return shareholder
			else:
				return False

		# if shareholder_name and :
		# 	return True
		# else:
		# 	return shareholder

	def recursive_test(self, shareholder_shares, share_transfer_shares):
		# return True if shares exist with the person
		# else False
		# writing un readable, but in efficient code
		if shareholder_shares == []:
			return False
		start, end = 0, 1
		if shareholder_shares[0][end] < share_transfer_shares[0][start]:
			shareholder_shares.pop(0)
			if len(shareholder_shares) == 0:
				return False
			return recursive_test(self, shareholder_shares, share_transfer_shares)
		
		is_in_range = self.check_if_in_range(shareholder_shares[0], share_transfer_shares[0])

		if is_in_range == True:
			if len(share_transfer_shares) == 1:
				return True
			else:
				share_transfer_shares.pop(0)
				return self.recursive_test(self, shareholder_shares, share_transfer_shares)
		elif is_in_range == False:
			return False
		else:
			share_transfer_shares[0] = is_in_range
			return self.recursive_test(self, shareholder_shares, share_transfer_shares)
		
		if shareholder_share[start] <= share_transfer_share[start] <= shareholder_share[stop]:
			self.check_if_in_range(shareholder_share, share_transfer_share)

	def check_if_in_range(self, shareholder_share, share_transfer_share):
		# if in range return True
		# if totally out of range return False
		# else return range not in range
		start, end = 0, 1
		if share_transfer_share[start] >= shareholder_share[start] and share_transfer_share[end] <= shareholder_share[end]:
			return True
		elif share_transfer_share[start] < shareholder_share[start]:
			return False
		else:
			return [shareholder_share[end]+1, share_transfer_share[end]]

	def add_shares(self):
		# add list of shares to to_shareholder
		shareholder = frappe.get_doc("Shareholder", self.to_shareholder)
		for share in self.shares:
			shareholder.append('share_ledger', {
				'company': self.company,
				'from_no': share.from_no,
				'to_no': share.to_no,
				'no_of_shares': (share.to_no - share.from_no + 1),
				'amount': self.rate * (share.to_no - share.from_no + 1),
				'rate': self.rate,
			})
		shareholder.save()

	def remove_shares(self):
		# remove share from from_shareholder
		shareholder = frappe.get_doc("Shareholder", self.from_shareholder)
		new_ledger = []
		
		shareholder = self.recursive_shareholder_edit(shareholder, 0, 0)
		shareholder.save()

	def recursive_shareholder_edit(self, shareholder, ledger_pointer, share_pointer):
		if share_pointer == len(self.shares):
			return shareholder
		if ledger_pointer == len(shareholder.share_ledger):
			frappe.throw('Something went wrong!')

		# shareholder_ledger : ======
		# sharetransfer_share:         ===
		if shareholder.share_ledger[ledger_pointer].to_no < self.shares[share_pointer].from_no:
			return self.recursive_shareholder_edit(shareholder, ledger_pointer+1, share_pointer)

		# shareholder_ledger : ======
		# sharetransfer_share:      ===
		if self.shares[share_pointer].from_no < shareholder.share_ledger[ledger_pointer].to_no < self.shares[share_pointer].to_no and \
			self.shares[share_pointer].from_no > shareholder.share_ledger[ledger_pointer].to_no:
			shareholder.share_ledger[ledger_pointer].to_no = self.shares[share_pointer].from_no - 1
			return self.recursive_shareholder_edit(shareholder, ledger_pointer, share_pointer)

		# shareholder_ledger :   ======
		# sharetransfer_share: ===
		if self.shares[share_pointer].from_no < shareholder.share_ledger[ledger_pointer].from_no < self.shares[share_pointer].to_no and \
			self.shares[share_pointer].from_no < shareholder.share_ledger[ledger_pointer].from_no:
			shareholder.share_ledger[ledger_pointer].from_no = self.shares[share_pointer].to_no + 1
			return self.recursive_shareholder_edit(shareholder, ledger_pointer, share_pointer+1)

		# shareholder_ledger : ======
		# sharetransfer_share:  ===
		if self.shares[share_pointer].from_no >= shareholder.share_ledger[ledger_pointer].from_no and \
			self.shares[share_pointer].to_no <= shareholder.share_ledger[ledger_pointer].to_no:
			# shareholder_ledger : ======
			# sharetransfer_share: ======
			if self.shares[share_pointer].from_no == shareholder.share_ledger[ledger_pointer].from_no or \
				self.shares[share_pointer].to_no == shareholder.share_ledger[ledger_pointer].to_no:
				shareholder.share_ledger[ledger_pointer].from_no = -1
				shareholder.share_ledger[ledger_pointer].to_no = -1
				return self.recursive_shareholder_edit(shareholder, ledger_pointer+1, share_pointer+1)

			# shareholder_ledger : ======
			# sharetransfer_share: ===
			elif self.shares[share_pointer].from_no == shareholder.share_ledger[ledger_pointer].from_no:
				shareholder.share_ledger[ledger_pointer].from_no = self.shares[share_pointer].to_no + 1
				return self.recursive_shareholder_edit(shareholder, ledger_pointer, share_pointer+1)

			# shareholder_ledger : ======
			# sharetransfer_share:    ===
			elif self.shares[share_pointer].to_no == shareholder.share_ledger[ledger_pointer].to_no:
				shareholder.share_ledger[ledger_pointer].to_no = self.shares[share_pointer].from_no - 1
				return self.recursive_shareholder_edit(shareholder, ledger_pointer, share_pointer+1)

			# shareholder_ledger : ======
			# sharetransfer_share:  ====
			elif self.shares[share_pointer].from_no == shareholder.share_ledger[ledger_pointer].from_no or \
				self.shares[share_pointer].to_no == shareholder.share_ledger[ledger_pointer].to_no:
				shareholder.append('share_ledger', {
					'company': self.company,
					'from_no': self.shares[share_pointer].to_no + 1,
					'to_no': shareholder.share_ledger[ledger_pointer].to_no,
					'no_of_shares': (shareholder.share_ledger[ledger_pointer].to_no - self.shares[share_pointer].to_no),
					'amount': self.rate * (shareholder.share_ledger[ledger_pointer].to_no - self.shares[share_pointer].to_no),
					'rate': self.rate
				})
				shareholder.share_ledger[ledger_pointer].to_no = self.shares[share_pointer].from_no - 1
				return self.recursive_shareholder_edit(shareholder, ledger_pointer, share_pointer+1)

		# shareholder_ledger :  ====
		# sharetransfer_share: ======
		if self.shares[share_pointer].from_no < shareholder.share_ledger[ledger_pointer].from_no and \
			self.shares[share_pointer].to_no > shareholder.share_ledger[ledger_pointer].to_no:
			shareholder.share_ledger[ledger_pointer].from_no = -1
			shareholder.share_ledger[ledger_pointer].to_no = -1
			return self.recursive_shareholder_edit(shareholder, ledger_pointer+1, share_pointer)