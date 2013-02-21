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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.	If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes

from webnotes.utils import flt
from webnotes.model import db_exists
from webnotes.model.doc import addchild
from webnotes.model.bean import copy_doclist

sql = webnotes.conn.sql
	

class DocType :
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	# Pull Item Details
	# ---------------------------
	def pull_item_details(self):
		if self.doc.return_type == 'Sales Return':
			if self.doc.delivery_note_no:
				det = sql("select t1.name, t1.item_code, t1.description, t1.qty, t1.uom, t2.export_rate * t3.conversion_rate, t3.customer, t3.customer_name, t3.customer_address, t2.serial_no, t2.batch_no from `tabDelivery Note Packing Item` t1, `tabDelivery Note Item` t2, `tabDelivery Note` t3 where t1.parent = t3.name and t2.parent = t3.name and t1.parent_detail_docname = t2.name and t3.name = '%s' and t3.docstatus = 1" % self.doc.delivery_note_no)
			elif self.doc.sales_invoice_no:
				det = sql("select t1.name, t1.item_code, t1.description, t1.qty, t1.stock_uom, t1.export_rate * t2.conversion_rate, t2.customer, t2.customer_name, t2.customer_address, t1.serial_no from `tabSales Invoice Item` t1, `tabSales Invoice` t2 where t1.parent = t2.name and t2.name = '%s' and t2.docstatus = 1" % self.doc.sales_invoice_no)
		elif self.doc.return_type == 'Purchase Return' and self.doc.purchase_receipt_no:
			det = sql("select t1.name, t1.item_code, t1.description, t1.received_qty, t1.uom, t1.purchase_rate, t2.supplier, t2.supplier_name, t2.supplier_address, t1.serial_no, t1.batch_no from `tabPurchase Receipt Item` t1, `tabPurchase Receipt` t2 where t1.parent = t2.name and t2.name = '%s' and t2.docstatus = 1" % self.doc.purchase_receipt_no)

		self.doc.cust_supp = det and det[0][6] or ''
		self.doc.cust_supp_name = det and det[0][7] or ''
		self.doc.cust_supp_address = det and det[0][8] or ''
		self.create_item_table(det)
		self.doc.save()
		
	# Create Item Table
	# -----------------------------
	def create_item_table(self, det):
		self.doclist = self.doc.clear_table(self.doclist, 'return_details', 1)
		for i in det:
			ch = addchild(self.doc, 'return_details', 'Sales and Purchase Return Item', 
				self.doclist)
			ch.detail_name = i and i[0] or ''
			ch.item_code = i and i[1] or ''
			ch.description = i and i[2] or ''
			ch.qty = i and flt(i[3]) or 0
			ch.uom = i and i[4] or ''
			ch.rate = i and flt(i[5]) or 0
			ch.serial_no = i and i[9] or ''
			ch.batch_no = (len(i) == 11) and i[10] or ''
			ch.save()

	# Clear return table
	# --------------------------------
	def clear_return_table(self):
		self.doclist = self.doc.clear_table(self.doclist, 'return_details', 1)
		self.doc.save()