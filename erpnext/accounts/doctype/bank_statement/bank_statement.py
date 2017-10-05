# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, csv, datetime, os
from frappe import _
from frappe.utils import flt, date_diff
from frappe.model.document import Document
from frappe.utils.file_manager import get_file_path, get_uploaded_content

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

	def convert_to_internal_format(self, csv_column_header, csv_row_field_value, bank_statement_mapping_items, eval_data):

		# select mapping_row from bank_statement_mapping_item where source_field = csv_column_header
		mapping_row = None
		for row in bank_statement_mapping_items:
			if row.source_field == csv_column_header:
				mapping_row = row
		if not mapping_row: return

		# transformation_rule from mapping_row.transformation_rule (should be a python snippet).
		transformation_rule = mapping_row.transformation_rule
		csv_row_field_value = self.eval_transformation(transformation_rule, mapping_row.source_field_abbr, eval_data)

		#if not csv_row_field_value:
		#	Deprecated (leave for now. Make a general return value preparation)
		#	if 'date' in str(mapping_row.target_field).lower():
		#		date_format = frappe.db.get_value("Bank Statement Format", self.bank_statement_format, 'date_format')
		#		strptime_format = dateformats.get(date_format)
		#		if strptime_format.index('%Y') == 0:
		#			year_index = 0
		#		else:
		#			year_index = 2
		#		date_str = prepare_date_str(csv_row_field_value, year_index)
		#		try:
		#			csv_row_field_value = str(datetime.datetime.strptime(date_str, strptime_format).date())  #00/00/0000
		#		except Exception as e9433:
		#			frappe.throw(_("Date format in attached file does not match that in bank statement format used"))

		#	if ('amount' in str(mapping_row.target_field).lower()) or ('balance' in str(mapping_row.target_field).lower()):
		#		csv_row_field_value = flt(csv_row_field_value)

		return mapping_row.target_field, csv_row_field_value

	def fill_table(self):
		if not self.file: return
		file_doc = frappe._dict()
		self.bank_statement_items = []
		bank_statement_format = frappe.get_doc("Bank Statement Format", self.bank_statement_format)
		bank_statement_mapping_items = bank_statement_format.bank_statement_mapping_item
		file_id = frappe.db.sql("""SELECT name FROM tabFile WHERE attached_to_doctype = '{0}' AND attached_to_name = '{1}'
						""".format("Bank Statement", self.name), as_dict=1)
		file_doc = frappe.get_doc("File",file_id[0].name)
		# load contents of CSV file into 2d array raw_bank_statement_items
		# create a list of maps, intermediate_bank_statement_items, to hold bank statement items based on internal > 
		# < representation see "Bank Statement Item" definition
		intermediate_bank_statement_items = []
		filename, file_extension = os.path.splitext(self.file)

		if file_extension == '.xlsx':
			from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file
			rows = read_xlsx_file_from_attached_file(file_id=file_doc.name)
		elif file_extension == '.csv':
			from frappe.utils.file_manager import get_file
			from frappe.utils.csvutils import read_csv_content
			fname, fcontent = get_file(file_doc.name)
			rows = read_csv_content(fcontent)
		else:
			frappe.throw(_("Unsupported File Format"))

		csv_header_list = rows[0]
		data_rows = rows[1:]

		# for each statement_row in raw_bank_statement_items:
		for statement_row in data_rows:
			bank_sta_item = dict()
			eval_data = self.get_data_for_eval(statement_row, csv_header_list, bank_statement_mapping_items)
			for column_index, column_value in enumerate(statement_row):
				itm = self.convert_to_internal_format(csv_header_list[column_index], column_value, bank_statement_mapping_items, eval_data)
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

		for sta in intermediate_bank_statement_items:
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

	def eval_transformation(self, eval_code, source_abbr, data):
		if not eval_code:
			frappe.msgprint(_("There is no eval code"))
			return
		try:
			code_type = get_code_type(eval_code.strip())
			if ':' in eval_code: eval_code = eval_code[eval_code.index(':')+1:]
			eval_data = data
			if code_type == 'condition':
				if not frappe.safe_eval(eval_code, None, eval_data):
					return None
			if code_type == 'date_format':
				eval_result = datetime.datetime.strptime(eval_data[source_abbr].strip(), eval_code.strip())
			if code_type == 'eval':
				eval_result = frappe.safe_eval(eval_code, None, eval_data)

			return eval_result

		except NameError as err:
			frappe.throw(_("Name error: {0}".format(err)))
		except SyntaxError as err:
			frappe.throw(_("Syntax error in formula or condition: {0}".format(err)))
		except Exception as e:
			frappe.throw(_("Error in formula or condition: {0}".format(e)))
			raise

	def get_data_for_eval(self, statement_row, csv_header_list, bank_statement_mapping_items):
		'''Returns data object for evaluating formula'''
		data = frappe._dict()
		for column_index, column_value in enumerate(statement_row):
			source_abbr = get_source_abbr(csv_header_list[column_index], bank_statement_mapping_items)
			if not source_abbr: continue
			data[source_abbr] = column_value

		return data

	def validate_dates(self): # ToDo
		if date_diff(self.end_date, self.start_date) < 0:
			frappe.throw(_("To date cannot be before From date"))

	def get_account_no(self):
		bank = frappe.get_doc("Bank", self.bank)
		ret_dict = {
			'acc_nos': [acc.account_number for acc in bank.bank_accounts],
			'currency_map': {acc.account_number:acc.currency for acc in bank.bank_accounts}
		}
		return ret_dict

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

def get_source_abbr(source_field, bank_statement_mapping_items):
	for row in bank_statement_mapping_items:
		if row.source_field == source_field:
			return row.source_field_abbr

def get_code_type(eval_code):
	eval_code = eval_code.lower()
	if eval_code.startswith('if'): return 'condition'
	if eval_code.startswith('date'): return 'date_format'
	if eval_code.startswith('eval'): return 'eval'
	return 'eval'
