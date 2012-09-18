# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Please edit this list and import only required elements
from __future__ import unicode_literals
import webnotes

from webnotes.utils import add_days, add_months, add_years, cint, cstr, date_diff, default_fields, flt, fmt_money, formatdate, generate_hash, getTraceback, get_defaults, get_first_day, get_last_day, getdate, has_common, month_name, now, nowdate, replace_newlines, sendmail, set_default, str_esc_quote, user_format, validate_email_add
from webnotes.model import db_exists
from webnotes.model.doc import Document, addchild, getchildren, make_autoname
from webnotes.model.doclist import getlist, copy_doclist
from webnotes.model.code import get_obj, get_server_obj, run_server_obj, updatedb, check_syntax
from webnotes import session, form, is_testing, msgprint, errprint

set = webnotes.conn.set
sql = webnotes.conn.sql
get_value = webnotes.conn.get_value
in_transaction = webnotes.conn.in_transaction
convert_to_lists = webnotes.conn.convert_to_lists
	
# -----------------------------------------------------------------------------------------

	
class DocType:
	def __init__( self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.pur_items = {}
		self.bom_list = []
		self.sub_assembly_items = []
		self.item_master = {}

	def traverse_bom_tree( self, bom_no, qty, ext_pur_items = 0, ext_sub_assembly_items = 0, calculate_cost = 0, maintain_item_master = 0 ):
		count, bom_list, qty_list = 0, [bom_no], [qty]
		while (count < len(bom_list)):
			# get child items from BOM MAterial Table.
			child_items = sql("select item_code, bom_no, qty, qty_consumed_per_unit from `tabBOM Item` where parent = %s", bom_list[count], as_dict = 1)
			child_items = child_items and child_items or []
			for item in child_items:
				# Calculate qty required for FG's qty.
				item['reqd_qty'] = flt(qty) * ((count == 0) and 1 or flt(qty_list[count]) )* flt(item['qty_consumed_per_unit'])

				# extracting Purchase Items
				if ext_pur_items and not item['bom_no']:
					self.pur_items[item['item_code']] = flt(self.pur_items.get(item['item_code'], 0)) + flt(item['reqd_qty'])
							
				# For calculate cost extracting BOM Items check for duplicate boms, this optmizes the time complexity for while loop.
				if calculate_cost and item['bom_no'] and (item['bom_no'] not in bom_list):
					bom_list.append(item['bom_no'])
					qty_list.append(item['reqd_qty'])

				# Here repeated bom are considered to calculate total qty of raw material required
				if not calculate_cost and item['bom_no']:
					bom_list.append(item['bom_no'])
					qty_list.append(item['reqd_qty'])

			count += 1
		return bom_list



	#	Raise Production Order
	def create_production_order(self,company, pp_items):
		"""Create production order. Called from Production Planning Tool"""
					 
		default_values = { 
			'posting_date'		: nowdate(),
			'origin'			: 'MRP',
			'wip_warehouse'		: '',
			'fg_warehouse'		: '',
			'status'			: 'Draft',
			'company'			: company,
			'fiscal_year'		: get_defaults()['fiscal_year'] 
		}
		pro_list = []

		for d in pp_items:
			pro_doc = Document('Production Order')
			for key in d.keys():
				pro_doc.fields[key] = d[key]

			for key in default_values:
				pro_doc.fields[key] = default_values[key]
			
			pro_doc.save(new = 1)
			pro_list.append(pro_doc.name)
			
		return pro_list


	def update_bom(self, bom_no):
		main_bom_list = self.traverse_bom_tree(bom_no, 1)
		main_bom_list.reverse()
		# run calculate cost and get
		for bom in main_bom_list:
			if bom and bom not in self.check_bom_list:
				bom_obj = get_obj('BOM', bom, with_children = 1)
				bom_obj.doc.save()
				bom_obj.check_recursion()
				bom_obj.update_flat_bom_engine()
				bom_obj.doc.docstatus = 1
				bom_obj.doc.save()
				self.check_bom_list.append(bom)
