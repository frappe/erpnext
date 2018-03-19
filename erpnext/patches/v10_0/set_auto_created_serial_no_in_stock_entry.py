# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	serialised_items = [d.name for d in frappe.get_all("Item", filters={"has_serial_no": 1})]

	if not serialised_items:
		return

	for dt in ["Stock Entry Detail", "Purchase Receipt Item", "Purchase Invoice Item"]:
		cond = ""
		if dt=="Purchase Invoice Item":
			cond = """ and parent in (select name from `tabPurchase Invoice`
				where `tabPurchase Invoice`.name = `tabPurchase Invoice Item`.parent and update_stock=1)"""

		item_rows = frappe.db.sql("""
			select name
			from `tab{0}`
			where conversion_factor != 1
				and docstatus = 1
				and ifnull(serial_no, '') = ''
				and item_code in ({1})
				{2}
		""".format(dt, ', '.join(['%s']*len(serialised_items)), cond), tuple(serialised_items))

		if item_rows:
			sle_serial_nos = dict(frappe.db.sql("""
				select voucher_detail_no, serial_no
				from `tabStock Ledger Entry`
				where ifnull(serial_no, '') != ''
					and voucher_detail_no in (%s)
			""".format(', '.join(['%s']*len(item_rows))),
				tuple([d[0] for d in item_rows])))

			batch_size = 100
			for i in range(0, len(item_rows), batch_size):
				batch_item_rows = item_rows[i:i + batch_size]
				when_then = []
				for item_row in batch_item_rows:
				
					when_then.append('WHEN `name` = "{row_name}" THEN "{value}"'.format(
						row_name=item_row[0],
						value=sle_serial_nos.get(item_row[0])))

				frappe.db.sql("""
					update
						`tab{doctype}`
					set
						serial_no = CASE {when_then_cond} ELSE `serial_no` END
				""".format(
					doctype = dt,
					when_then_cond=" ".join(when_then)
				))