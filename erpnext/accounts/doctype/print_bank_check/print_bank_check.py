# -*- coding: utf-8 -*-
# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class PrintBankCheck(Document):
	def validate(self):
		self.get_transaction()
		self.add_journal_entry()
	
	def get_transaction(self):
		doc = frappe.get_doc("Bank Transactions", self.bank_transaction)

		if doc.amount_of == None:
			frappe.throw(_("This transaction no is a bank check."))

		self.mesAString(doc.date_data)

		amount_of = ""
		amount_of_split = doc.amount_of.split(" ")

		amount_of_split.pop(0)
		amount_of_split.remove("solo.")

		for i in amount_of_split:
			amount_of += i + " "
		
		str_amount = str(doc.amount)
		
		split_amount = str_amount.split(".")

		self.amount = "***"
		# if len(split_amount) == 1:
		# 	self.amount = str_amount
		# 	self.amount += ".00"
		# if len(split_amount) == 2:
		# 	if split_amount[1] == "0":
		# 		self.amount = split_amount[0]
		# 		self.amount += ".00"
		# 	else:
		# 		self.amount = str_amount
		self.amount += self.SetMoneda(doc.amount, 2)
		self.amount += "***"
		self.amount_of = "***"
		self.amount_of += amount_of
		self.amount_of += "***"

	def SetMoneda(nume, num, n_decimales):
		n_decimales = abs(n_decimales)
		num = round(num, n_decimales)
		num, dec = str(num).split(".")
		dec += "0" * (n_decimales - len(dec))
		num = num[::-1]

		arr_inverse = [num[pos:pos+3][::-1] for pos in range(0,50,3) if (num[pos:pos+3])]

		arr = []
		idx = len(arr_inverse) - 1

		while (idx >= 0):
			arr.append(arr_inverse[idx])
			idx = idx - 1
    	
		num = str.join(",", arr)

		try:
			if num[0:2] == "-,":
				num = "-%s" % num[2:]

		except IndexError:
			pass

		if not n_decimales:
			return "%s" % (num)
        
		return "%s.%s" % (num, dec)

	def add_journal_entry(self):
		self.delte_rows()
		entries = frappe.get_all("Journal Entry", ["name"], filters = {"bank_transaction": self.bank_transaction, "docstatus": 1})

		count = 0

		if len(entries) == 0:
			frappe.throw(_("No exist journal entry."))

		for entry in entries:
			accounts = frappe.get_all("Journal Entry Account", ["*"], filters = {"parent": entry.name})

			for account in accounts:
				doc = frappe.get_doc("Account", account.account)
				row = self.append("detail", {})
				row.cuenta = doc.account_number
				row.descripcion = doc.name
				row.debit = account.debit_in_account_currency
				row.credit = account.credit_in_account_currency
				count += 1

				if count == 6:
					break
			
			if count == 6:
				break
				
	
	def delte_rows(self):
		rows = frappe.get_all("Print Bank Check Detail", ["name"], filters = {"parent": self.name})
		for row in rows:
			frappe.delete_doc("Print Bank Check Detail", row.name)

	def mesAString(self, date):
		m = {
			'01': "ENERO",
			'02': "FEBRERO",
			'03': "MARZO",
			'04': "ABRIL",
			'05': "MAYO",
			'06': "JUNIO",
			'07': "JULIO",
			'08': "AGOSTO",
			'09': "SEPTIEMBRE",
			'10': "OCTUBRE",
			'11': "NOVIEMBRE",
			'12': "DICIEMBRE"
			}

		date_str = date.strftime('%d-%m-%Y')
		date_split = date_str.split("-")
		dia =  date_split[0]
		mes =  date_split[1]
		anio = date_split[2]

		try:
			out = str(m[mes])
			self.place_date = "San Pedro Sula, Cortés, " + dia + " de " + out + " del " + anio
		except:
			raise ValueError('No es un mes')