# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import print_function, unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate
from frappe.utils.password import get_decrypted_password

class WebAcademyApplicant(Document):
	def before_insert(self):
		# Before a new document is saved
		self.check_if_student_account_already_exists(self.student_email_address)
		
	def after_insert(self):
		# After the application is inserted in the database, create a new student
		self.create_new_student()

	def check_if_student_account_already_exists(self, email):
		# Check if a student account alread exists, if it does, throw an error
		get_accounts = frappe.get_all('Student', filters={'student_email_id': email})
		if len(get_accounts) != 0:
			frappe.throw('Student with Email {0} already Exists.'.format(self.student_email_address))

	def create_new_student(self):
		student = frappe.get_doc({
			'doctype': 'Student',
			'student_email_id': self.student_email_address,
			'first_name': self.first_name,
			'last_name': self.last_name,
			'middle_name': self.middle_name
		})
		student_user_account = frappe.get_doc({
			'doctype': 'User',
			'email': self.student_email_address,
			'first_name': self.first_name,
			'last_name': self.last_name,
			'new_passsword': get_decrypted_password(self.doctype, self.name, 'password')

		})
		student.save()
		if(self.lms_user == 1):
			student_user_account.add_roles("LMS User")
		else:
			student_user_account.add_roles("Student", "LMS User")
		student_user_account.save()