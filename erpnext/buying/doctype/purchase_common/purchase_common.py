# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _

from erpnext.stock.doctype.item.item import get_last_purchase_details
from erpnext.controllers.buying_controller import BuyingController

class PurchaseCommon(BuyingController):
	def update_last_purchase_rate(self, obj, is_submit):
		"""updates last_purchase_rate in item table for each item"""

		import frappe.utils
		this_purchase_date = frappe.utils.getdate(obj.get('posting_date') or obj.get('transaction_date'))

		for d in obj.get("items"):
			# get last purchase details
			last_purchase_details = get_last_purchase_details(d.item_code, obj.name)

			# compare last purchase date and this transaction's date
			last_purchase_rate = None
			if last_purchase_details and \
					(last_purchase_details.purchase_date > this_purchase_date):
				last_purchase_rate = last_purchase_details['base_rate']
			elif is_submit == 1:
				# even if this transaction is the latest one, it should be submitted
				# for it to be considered for latest purchase rate
				if flt(d.conversion_factor):
					last_purchase_rate = flt(d.base_rate) / flt(d.conversion_factor)
				else:
					frappe.throw(_("UOM Conversion factor is required in row {0}").format(d.idx))

			# update last purchsae rate
			if last_purchase_rate:
				frappe.db.sql("""update `tabItem` set last_purchase_rate = %s where name = %s""",
					(flt(last_purchase_rate), d.item_code))

	def validate_for_items(self, obj):
		check_list, chk_dupl_itm=[],[]
		for d in obj.get("items"):
			# validation for valid qty
			if flt(d.qty) < 0 or (d.parenttype != 'Purchase Receipt' and not flt(d.qty)):
				frappe.throw(_("Please enter quantity for Item {0}").format(d.item_code))

			# udpate with latest quantities
			bin = frappe.db.sql("""select projected_qty from `tabBin` where
				item_code = %s and warehouse = %s""", (d.item_code, d.warehouse), as_dict=1)

			f_lst ={'projected_qty': bin and flt(bin[0]['projected_qty']) or 0, 'ordered_qty': 0, 'received_qty' : 0}
			if d.doctype == 'Purchase Receipt Item':
				f_lst.pop('received_qty')
			for x in f_lst :
				if d.meta.get_field(x):
					d.set(x, f_lst[x])

			item = frappe.db.sql("""select is_stock_item, is_purchase_item,
				is_sub_contracted_item, end_of_life from `tabItem` where name=%s""", d.item_code)

			from erpnext.stock.doctype.item.item import validate_end_of_life
			validate_end_of_life(d.item_code, item[0][3])

			# validate stock item
			if item[0][0]=='Yes' and d.qty and not d.warehouse:
				frappe.throw(_("Warehouse is mandatory for stock Item {0} in row {1}").format(d.item_code, d.idx))

			# validate purchase item
			if not (obj.doctype=="Material Request" and getattr(obj, "material_request_type", None)=="Material Transfer"):
				if item[0][1] != 'Yes' and item[0][2] != 'Yes':
					frappe.throw(_("{0} must be a Purchased or Sub-Contracted Item in row {1}").format(d.item_code, d.idx))

			# list criteria that should not repeat if item is stock item
			e = [getattr(d, "schedule_date", None), d.item_code, d.description, d.warehouse, d.uom,
				d.meta.get_field('prevdoc_docname') and d.prevdoc_docname or d.meta.get_field('sales_order_no') and d.sales_order_no or '',
				d.meta.get_field('prevdoc_detail_docname') and d.prevdoc_detail_docname or '',
				d.meta.get_field('batch_no') and d.batch_no or '']

			# if is not stock item
			f = [getattr(d, "schedule_date", None), d.item_code, d.description]

			ch = frappe.db.sql("""select is_stock_item from `tabItem` where name = %s""", d.item_code)

			if ch and ch[0][0] == 'Yes':
				# check for same items
				if e in check_list:
					frappe.throw(_("Item {0} has been entered multiple times with same description or date or warehouse").format(d.item_code))
				else:
					check_list.append(e)

			elif ch and ch[0][0] == 'No':
				# check for same items
				if f in chk_dupl_itm:
					frappe.throw(_("Item {0} has been entered multiple times with same description or date").format(d.item_code))
				else:
					chk_dupl_itm.append(f)

	def check_for_stopped_status(self, doctype, docname):
		stopped = frappe.db.sql("""select name from `tab%s` where name = %s and
			status = 'Stopped'""" % (doctype, '%s'), docname)
		if stopped:
			frappe.throw(_("{0} {1} status is 'Stopped'").format(doctype, docname), frappe.InvalidStatusError)

	def check_docstatus(self, check, doctype, docname, detail_doctype = ''):
		if check == 'Next':
			submitted = frappe.db.sql("""select t1.name from `tab%s` t1,`tab%s` t2
				where t1.name = t2.parent and t2.prevdoc_docname = %s and t1.docstatus = 1"""
				% (doctype, detail_doctype, '%s'), docname)
			if submitted:
				frappe.throw(_("{0} {1} has already been submitted").format(doctype, submitted[0][0]))

		if check == 'Previous':
			submitted = frappe.db.sql("""select name from `tab%s`
				where docstatus = 1 and name = %s""" % (doctype, '%s'), docname)
			if not submitted:
				frappe.throw(_("{0} {1} is not submitted").format(doctype, submitted[0][0]))
