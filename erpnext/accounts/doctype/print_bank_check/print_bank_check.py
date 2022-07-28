# -*- coding: utf-8 -*-
# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class PrintBankCheck(Document):
	# def validate(self):
	# 	self.get_transaction()
	# 	self.add_journal_entry()
	
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
		
		self.amount_of = amount_of
		self.amount = doc.amount

	def add_journal_entry(self):
		self.delte_rows()
		entries = frappe.get_all("Journal Entry", ["name"], filters = {"bank_transaction": self.bank_transaction, "docstatus": 1})

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