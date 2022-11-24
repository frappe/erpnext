# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
import re
import datetime

class BankPaymentSettings(Document):
	def validate(self):
		self.validate_upload_path()

	def validate_upload_path(self):
		get_upload_path(self.upload_path)

def check_date_formats(date_string):
	temp = date_string.replace('_','.').replace('-','.').split('.')
	now  = datetime.datetime.now()
	for i in temp:
		if i and i.lower() not in ('dd','mm','mon','month','yy','yyyy'):
			frappe.throw(_("<code>Error: Invalid date format string `{}` in `File Upload Path`</code>").format(i),title="Error")

		if i.lower() == 'dd':
			date_string = str(date_string).replace(i, str(now.strftime('%d')))
		elif i.lower() == 'mm':
			date_string = str(date_string).replace(i, str(now.strftime('%m')))
		elif i.lower() == 'mon':
			date_string = str(date_string).replace(i, str(now.strftime('%b')))
		elif i.lower() == 'month':
			date_string = str(date_string).replace(i, str(now.strftime('%B')))
		elif i.lower() == 'yy':
			date_string = str(date_string).replace(i, str(now.strftime('%y')))
		elif i.lower() == 'yyyy':
			date_string = str(date_string).replace(i, str(now.strftime('%Y')))
	return date_string

def check_special_characters(sc,format_string):
	regex = re.compile(sc)
	if(regex.search(format_string) == None):
		pass
	else:
		frappe.throw(_("<code>Error: Special characters not permitted  \
			near <b>{}</b> in `File Upload Path`</code><pre>Special Characters: {}</pre>")\
			.format(format_string,sc.strip('[').strip(']')),title="Error")

def get_upload_path(upload_path):
	formatted_path = []
	for i in str(upload_path).split('/'):
		temp_dir = i
		if i.startswith('{') and not i.endswith('}'):
			frappe.throw(_("<code>Error: `File Upload Path` missing closing brace '}}' near {}</code>").format(i),title="Error")
		elif not i.startswith('{') and i.endswith('}'):
			frappe.throw(_("<code>Error: `File Upload Path` missing opening brace '{{' near {}</code>").format(i),title="Error")
		elif not i.startswith('{') and not i.endswith('}'):
			sc   = '[@!#$%^&*()\]\[<>?/\\\|}{~:,.\'\"]'
			check_special_characters(sc,i)
		elif i.count("{}"):
			frappe.throw(_("<code>Error: Empty braces {} not permitted in `File Upload Path`</code>"),title="Error")
		elif i.startswith('{') and i.endswith('}'):
			sc   = '[@!#$%^&*()\]\[<>?/\|}{~:,\'\"]'
			temp = i[1:len(i)-1]
			check_special_characters(sc,temp)
			temp_dir = check_date_formats(temp)
		formatted_path.append(temp_dir)

	return '/'.join(formatted_path)
