# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, json
from frappe import _
from frappe.utils import nowdate
from erpnext.setup.utils import get_exchange_rate
from frappe.core.doctype.communication.email import make
from erpnext.stock.get_item_details import get_pos_profile
from erpnext.accounts.party import get_party_account_currency
from erpnext.controllers.accounts_controller import get_taxes_and_charges

@frappe.whitelist()
def get_items(price_list, item=None):
	condition = ""
	order_by = ""

	if item:
		# search serial no
		item_code = frappe.db.sql("""select name as serial_no, item_code
			from `tabSerial No` where name=%s""", (item), as_dict=1)
		if item_code:
			item_code[0]["name"] = item_code[0]["item_code"]
			return item_code

		# search barcode
		item_code = frappe.db.sql("""select name, item_code from `tabItem`
			where barcode=%s""",
			(item), as_dict=1)
		if item_code:
			item_code[0]["barcode"] = item
			return item_code

	# locate function is used to sort by closest match from the beginning of the value
	return frappe.db.sql("""select i.name as item_code, i.item_name, i.image as item_image,
		item_det.price_list_rate, item_det.currency
		from `tabItem` i LEFT JOIN
			(select item_code, price_list_rate, currency from
				`tabItem Price`	where price_list=%(price_list)s) item_det
		ON
			(item_det.item_code=i.name or item_det.item_code=i.variant_of)
		where
			i.disabled = 0 and i.has_variants = 0
			and (i.item_code like %(item_code)s
			or i.item_name like %(item_code)s)
		limit 24""", {'item_code': '%%%s%%'%(frappe.db.escape(item)), 'price_list': price_list} , as_dict=1)
