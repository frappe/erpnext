# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from datetime import datetime, timedelta, date

class AccountStatementPayment(Document):
	def validate(self):
		if self.docstatus == 1:
			self.assign_cai()
	
	def initial_number(self, number):

		if number >= 1 and number < 10:
			return("0000000" + str(number))
		elif number >= 10 and number < 100:
			return("000000" + str(number))
		elif number >= 100 and number < 1000:
			return("00000" + str(number))
		elif number >= 1000 and number < 10000:
			return("0000" + str(number))
		elif number >= 10000 and number < 100000:
			return("000" + str(number))
		elif number >= 100000 and number < 1000000:
			return("00" + str(number))
		elif number >= 1000000 and number < 10000000:
			return("0" + str(number))
		elif number >= 10000000:
			return(str(number))

	def assign_cai(self):
		user = frappe.session.user
		gcai_allocation = frappe.get_all("GCAI Allocation", ["branch", "pos"], filters = {"user": user, "company": self.company, "type_document": self.type_document})

		if not gcai_allocation:
			frappe.throw(_("The user {} does not have an assigned CAI".format(user)))

		for item in gcai_allocation:
			cais = frappe.get_all("GCAI", ["codedocument", "codebranch", "codepos","initial_range", "final_range", "current_numbering", "name", "cai", "due_date"], filters = {"company": self.company, "sucursal": item.branch, "pos_name": item.pos, "state": "Valid", "type_document": self.type_document})
			
			if not cais:
				frappe.throw(_("There is no CAI available to generate this invoice."))

			for cai in cais:
				if str(cai.due_date) < str(datetime.now()):
					self.validate_cai(cai.name)

					if len(cais) == 1:
						frappe.throw(_("The CAI {} arrived at its expiration day.".format(cai.cai)))
					
					continue
									
				if cai.current_numbering > cai.final_range:					
					self.validate_cai(cai.name)

					if len(cais) == 1:
						frappe.throw(_("The CAI {} reached its limit numbering.".format(cai.cai)))
					
					continue

				initial_range = self.initial_number(cai.initial_range)
				final_range = self.initial_number(cai.final_range)
				number = self.initial_number(cai.current_numbering)

				self.cai = cai.cai

				self.authorized_range = "{} - {}".format(initial_range, final_range)

				self.cashier = user

				self.numeration = "{}-{}-{}-{}".format(cai.codebranch, cai.codepos, cai.codedocument, number)

				doc = frappe.get_doc("GCAI", cai.name)
				doc.current_numbering += 1 
				doc.save()

				amount = int(cai.final_range) - int(cai.current_numbering)
				self.alerts(cai.due_date, amount)
				break
	
	def alerts(self, date, amount):
		gcai_setting = frappe.get_all("GCai Settings", ["expired_days", "expired_amount"])

		if len(gcai_setting) > 0:
			if amount <= gcai_setting[0].expired_amount:
				frappe.msgprint(_("There are only {} numbers available for this CAI.".format(amount)))
		
			now = date.today()
			days = timedelta(days=int(gcai_setting[0].expired_days))

			sum_dates = now+days

			if str(date) <= str(sum_dates):
				for i in range(int(gcai_setting[0].expired_days)):		
					now1 = date.today()
					days1 = timedelta(days=i)

					sum_dates1 = now1+days1
					if str(date) == str(sum_dates1):
						frappe.msgprint(_("This CAI expires in {} days.".format(i)))
						break		
					
	def validate_cai(self, name):
		doc_duedate = frappe.get_doc("GCAI", name)
		doc_duedate.state = "{}".format("Expired")
		doc_duedate.save()