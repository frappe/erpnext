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

from __future__ import unicode_literals
import webnotes
from webnotes.utils import add_days, cint,flt, nowdate, get_url_to_form, formatdate
from webnotes import msgprint, _
sql = webnotes.conn.sql

import webnotes.defaults


class DocType:	
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		
	def validate(self):
		if not self.doc.stock_uom:
			self.doc.stock_uom = webnotes.conn.get_value('Item', self.doc.item_code, 'stock_uom')
		
		if not self.doc.warehouse_type:
			self.doc.warehouse_type = webnotes.conn.get_value("Warehouse", self.doc.warehouse,
				"warehouse_type")
		
		self.validate_mandatory()
		
		self.doc.projected_qty = flt(self.doc.actual_qty) + flt(self.doc.ordered_qty) + \
		 	flt(self.doc.indented_qty) + flt(self.doc.planned_qty) - flt(self.doc.reserved_qty)
		
	def validate_mandatory(self):
		qf = ['actual_qty', 'reserved_qty', 'ordered_qty', 'indented_qty']
		for f in qf:
			if (not self.doc.fields.has_key(f)) or (not self.doc.fields[f]): 
				self.doc.fields[f] = 0.0
		
	def update_stock(self, args):
		self.update_qty(args)
		
		if args.get("actual_qty"):
			from stock.stock_ledger import update_entries_after
			
			if not args.get("posting_date"):
				args["posting_date"] = nowdate()
			
			# update valuation and qty after transaction for post dated entry
			update_entries_after({
				"item_code": self.doc.item_code,
				"warehouse": self.doc.warehouse,
				"posting_date": args.get("posting_date"),
				"posting_time": args.get("posting_time")
			})
			
	def update_qty(self, args):
		# update the stock values (for current quantities)
		self.doc.actual_qty = flt(self.doc.actual_qty) + flt(args.get("actual_qty"))
		self.doc.ordered_qty = flt(self.doc.ordered_qty) + flt(args.get("ordered_qty"))
		self.doc.reserved_qty = flt(self.doc.reserved_qty) + flt(args.get("reserved_qty"))
		self.doc.indented_qty = flt(self.doc.indented_qty) + flt(args.get("indented_qty"))
		self.doc.planned_qty = flt(self.doc.planned_qty) + flt(args.get("planned_qty"))
		
		self.doc.projected_qty = flt(self.doc.actual_qty) + flt(self.doc.ordered_qty) + \
		 	flt(self.doc.indented_qty) + flt(self.doc.planned_qty) - flt(self.doc.reserved_qty)
		
		self.doc.save()
		
		if (flt(args.get("actual_qty")) < 0 or flt(args.get("reserved_qty")) > 0) \
				and args.get("is_cancelled") == 'No' and args.get("is_amended")=='No':
			self.reorder_item(args.get("voucher_type"), args.get("voucher_no"))
		
	def get_first_sle(self):
		sle = sql("""
			select * from `tabStock Ledger Entry`
			where item_code = %s
			and warehouse = %s
			and ifnull(is_cancelled, 'No') = 'No'
			order by timestamp(posting_date, posting_time) asc, name asc
			limit 1
		""", (self.doc.item_code, self.doc.warehouse), as_dict=1)
		return sle and sle[0] or None

	def reorder_item(self,doc_type,doc_name):
		""" Reorder item if stock reaches reorder level"""
		if not hasattr(webnotes, "auto_indent"):
			webnotes.auto_indent = webnotes.conn.get_value('Global Defaults', None, 'auto_indent')

		if webnotes.auto_indent:
			#check if re-order is required
			item_reorder = webnotes.conn.get("Item Reorder", 
				{"parent": self.doc.item_code, "warehouse": self.doc.warehouse})
			if item_reorder:
				reorder_level = item_reorder.warehouse_reorder_level
				reorder_qty = item_reorder.warehouse_reorder_qty
				material_request_type = item_reorder.material_request_type or "Purchase"
			else:
				reorder_level, reorder_qty = webnotes.conn.get_value("Item", self.doc.item_code,
					["re_order_level", "re_order_qty"])
				material_request_type = "Purchase"
			
			if flt(reorder_qty) and flt(self.doc.projected_qty) < flt(reorder_level):
				self.create_material_request(doc_type, doc_name, reorder_level, reorder_qty,
					material_request_type)

	def create_material_request(self, doc_type, doc_name, reorder_level, reorder_qty,
			material_request_type="Purchase"):
		"""	Create indent on reaching reorder level	"""
		defaults = webnotes.defaults.get_defaults()
		item = webnotes.doc("Item", self.doc.item_code)
		
		mr = webnotes.bean([{
			"doctype": "Material Request",
			"company": defaults.company,
			"fiscal_year": defaults.fiscal_year,
			"transaction_date": nowdate(),
			"material_request_type": material_request_type,
			"remark": _("This is an auto generated Material Request.") + \
				_("It was raised because the (actual + ordered + indented - reserved) quantity reaches re-order level when the following record was created") + \
				": " + _(doc_type) + " " + doc_name
		}, {
			"doctype": "Material Request Item",
			"parenttype": "Material Request",
			"parentfield": "indent_details",
			"item_code": self.doc.item_code,
			"schedule_date": add_days(nowdate(),cint(item.lead_time_days)),
			"uom":	self.doc.stock_uom,
			"warehouse": self.doc.warehouse,
			"item_name": item.item_name,
			"description": item.description,
			"item_group": item.item_group,
			"qty": reorder_qty,
			"brand": item.brand,
		}])
		mr.insert()
		mr.submit()

		msgprint("""Item: %s is to be re-ordered. Material Request %s raised. 
			It was generated from %s: %s""" % 
			(self.doc.item_code, mr.doc.name, doc_type, doc_name))

		if(item.email_notify):
			self.send_email_notification(doc_type, doc_name, mr)
			
	def send_email_notification(self, doc_type, doc_name, bean):
		""" Notify user about auto creation of indent"""
		
		from webnotes.utils.email_lib import sendmail
		email_list=[d[0] for d in sql("""select distinct r.parent from tabUserRole r, tabProfile p
			where p.name = r.parent and p.enabled = 1 and p.docstatus < 2
			and r.role in ('Purchase Manager','Material Manager') 
			and p.name not in ('Administrator', 'All', 'Guest')""")]
		
		msg="""A new Material Request has been raised for Item: %s and Warehouse: %s \
			on %s due to %s: %s. See %s: %s """ % (self.doc.item_code, self.doc.warehouse,
				formatdate(), doc_type, doc_name, bean.doc.doctype, 
				get_url_to_form(bean.doc.doctype, bean.doc.name))
		
		sendmail(email_list, subject='Auto Material Request Generation Notification', msg = msg)
		
