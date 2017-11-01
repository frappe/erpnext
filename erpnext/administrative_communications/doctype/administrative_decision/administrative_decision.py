# -*- coding: utf-8 -*-
# Copyright (c) 2015, Erpdeveloper.team and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import datetime
from frappe.utils import flt, getdate
from frappe.utils import cint
from frappe import _
from frappe.utils import nowdate, add_days
import frappe.desk.form.assign_to

from frappe.model.document import Document
from frappe.model.naming import make_autoname

class AdministrativeDecision(Document):

	def autoname(self):
		# if self.type == "Coming" :
		# 	self.naming_series = "AD-IN/"
		# elif self.type == "Out" :
		# 	self.naming_series = "AD-OUT/"
		# elif self.type == "Inside" :
		# 	self.naming_series = "AD-INSIDE/"
		# else:
		# 	self.naming_series = "AD/"
			
		naming_method = frappe.db.get_value("HR Settings", None, "emp_created_by")
		if not naming_method:
			throw(_("Please setup Employee Naming System in Human Resource > HR Settings"))
		else:
			if naming_method == 'Naming Series':
				self.name = make_autoname(self.naming_series + '.####')
		self.transaction_number = self.name

		if self.type == "Out" :
			self.issued_number = self.name	


	def validate(self):
		# self.validate_dates()
		self.check_employee()
		# self.check_branch_department()
		# self.validate_fields()
		if self.get('docstatus') == 1:
			self.validate_approve()
			# if self.state != "Active" and  not self.get('__islocal'):
			# 	frappe.throw(_("All board must Approve before submitted"))


	def on_update(self):
		self.assign_to_admins()

	def assign_to_admins(self):
		pass


	# def validate_dates(self):
	# 	if getdate(self.start_date) > getdate(self.end_date):
	# 		frappe.throw(_("End Date can not be less than Start Date"))
			
	def check_employee(self) :
		if self.type == "Inside" :
			if not self.employee:
				frappe.throw(_("Employee Missing"))
		elif self.type == "Coming":
			if not self.coming_from:
				frappe.throw(_("The Issued Address Missing"))

	# def check_branch_department(self):
	# 	if self.type == "Inside" :
	# 		if not self.department or not self.branch:
	# 			frappe.throw(_("Add Branch and Department information"))
	# 		if not self.start_date:
	# 			frappe.throw(_("Add Start Date"))

	# def validate_fields(self):
	# 	if self.type == "Out":
	# 		if not self.start_date:
	# 			frappe.throw(_("Add Start Date"))
		# if self.type == "Out" or self.type == "Coming" :
		# 	if not self.end_date:
		# 		frappe.throw(_("Add End Date"))

	def validate_approve(self):
		checker = 1
		decision = self.administrative_board
		if decision:
			for d in self.administrative_board :
				if d.decision != "Approve":
					checker =0
			if checker==1:
				self.state = "Active"


	def change_administrative_board_decision(self,decision):
		administrative_board = frappe.get_doc('Administrative Board',{'parent' :self.name ,
		'user_id':frappe.session.user } )		# self.administrative_board
		if administrative_board :
			administrative_board.set("decision",decision)
			administrative_board.save()
		return administrative_board
