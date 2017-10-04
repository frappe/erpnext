# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.document import Document
import csv, datetime
from frappe.utils.file_manager import get_file_path

dateformats = {
	'1990-01-31': '%Y-%m-%d',
	'31-01-1990': '%d-%m-%Y',
	'31/01/1990': '%d/%m/%Y',
	'31.01.1990': '%d.%m.%Y',
	'01/31/1990': '%m/%d/%Y',
	'01-31-1990': '%m-%d-%Y',
	'1990-JAN-31': '%Y-%b-%d',
	'31-JAN-1990': '%d-%b-%Y',
	'31/JAN/1990': '%d/%b/%Y',
	'31.JAN.1990': '%d.%b.%Y',
	'JAN/31/1990': '%b/%d/%Y',
	'JAN-31-1990': '%b-%d-%Y',
}

class BankStatement(Document):
	def validate_file_format(self):
		if not self.file: return
		if not self.check_file_format(): frappe.throw(_("File Format check failed!"))

	def check_file_format(self):
		
		# verify that format of self.file is same as specification described in self.bank_statement_format (and its child > 
		# table bank_statement_format.bank_statment_mapping_item)
		sta_format = frappe.get_doc("Bank Statement Format",self.bank_statment_format)
		try:
			with open(get_file_path(self.file),"rb") as file:
				header = None
				for index,contnt in enumerate(file):
					if index == 0:
						header = contnt
						break
				if sta_format.statement_format == 'csv':
					fields_expected = [f.source_field for f in sta_format.bank_statement_mapping_items]
					if not set(fields_expected) <= set(header):
						return False
				if format.statement_format == 'next_format':
					print 'and so on...'
			return True
		except:
			frappe.log_error(frappe.get_traceback(), 'bank statement format error')
			return False

	def convert_to_internal_format(self, csv_column_header, csv_row_field_value, bank_statement_mapping_items):

		# select mapping_row from bank_statement_mapping_item where source_field = csv_column_header
		mapping_row = None
		for row in bank_statement_mapping_items:
			if row.source_field == csv_column_header:
				mapping_row = row
		if not mapping_row: return

		# transformation_rule from mapping_row.transformation_rule (should be a python snippet).
		transformation_rule = mapping_row.transformation_rule
		# result = apply_rule(transformation_rule, data_to_use)fmt
		if 'date' in str(mapping_row.target_field).lower():
			date_format = frappe.db.get_value("Bank Statement Format", self.bank_statement_format, 'date_format')
			strptime_format = dateformats.get(date_format)
			if strptime_format.index('%Y') == 0:
				year_index = 0
			else:
				year_index = 2
			date_str = prepare_date_str(csv_row_field_value, year_index)
			try:
				csv_row_field_value = str(datetime.datetime.strptime(date_str, strptime_format).date())  #00/00/0000
			except Exception as e9433:
				frappe.throw(_("Date format in attached file does not match that in bank statement format used"))

		if ('amount' in str(mapping_row.target_field).lower()) or ('balance' in str(mapping_row.target_field).lower()):
			csv_row_field_value = flt(csv_row_field_value)
		return mapping_row.target_field, csv_row_field_value

	def fill_table(self):
		self.bank_statement_items = []
		bank_statement_format = frappe.get_doc("Bank Statement Format", self.bank_statement_format)
		bank_statement_mapping_items = bank_statement_format.bank_statement_mapping_item

		# load contents of CSV file into 2d array raw_bank_statement_items
		# create a list of maps, intermediate_bank_statement_items, to hold bank statement items based on internal > 
		# < representation see "Bank Statement Item" definition
		intermediate_bank_statement_items = []

		# for each statement_row in raw_bank_statement_items:
		with open(get_file_path(self.file),"rb") as csv_file:
			csv_file_content = csv.reader(csv_file)
			for index, statement_row in enumerate(csv_file_content): # exclude header
				bank_sta_item = dict()
				if index == 0:
					csv_header_list = statement_row
					continue
				for column_index, column_value in enumerate(statement_row):
					print "CSV csv_header_list"
					print csv_header_list
					itm = self.convert_to_internal_format(csv_header_list[column_index], column_value, bank_statement_mapping_items)
					if not itm: continue
					target_field, eval_result = itm
					if target_field <> "txn_type":
						# add eval_result to the appropriate row and column in intermediate_bank_statement_items
						bank_sta_item[frappe.scrub(target_field)] = eval_result
					elif target_field == "txn_type":
						txn_type = get_txn_type(eval_result)	
						# add txn_type to the appropriate row and column in intermediate_bank_statement_items
						bank_sta_item[frappe.scrub(txn_type)] = txn_type
				intermediate_bank_statement_items.append(bank_sta_item) if bank_sta_item else None
		print intermediate_bank_statement_items
		for sta in intermediate_bank_statement_items:
			print '\n\nStatement Appended\n\n'
			print sta
			self.append('bank_statement_items', sta)  # create bank_statement_item table entries
		self.save()

	def process_statement(self):
		if not self.file: frappe.throw("No statement file present")
		if not self.validate_file_format: frappe.throw(_("File format mismatch"))
		#with open(get_file_path(self.file)) as f_h:
		#	header = None
		#	for index,row in enumerate(csv.reader(f_h)):
		#		if index == 0:
		#			header = row
		#			continue
		#		self.append

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def prepare_date_str(s,idx=2):
	separator = '/'
	date_str = s.strip()
	for sep in [',','/','.','-']:
		if sep in s:
			separator = sep
			date_str = date_str.split(sep)
			break
	for i,n in enumerate(date_str):
		if (i != idx) and is_number(n):
			if len(str(n)) < 2:
				date_str[i] = '0{}'.format(n)
	if idx == 0:
		dt_year = date_str[0]
	else:
		dt_year = date_str[2]
	if len(str(dt_year)) <= 2:
		if (int(dt_year) + 2000) <= int(frappe.utils.now().split('-',1)[0]):
			dt_year = '20{}'.format(dt_year)
		else:
			dt_year = '19{}'.format(dt_year)
	date_str[idx] = dt_year
	return separator.join(date_str)
