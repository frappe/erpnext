# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe


from frappe.model.document import Document

class QualityInspection(Document):
	def get_item_specification_details(self):
		self.set('readings', [])
		variant_of = frappe.db.get_value("Item", self.item_code, "variant_of")
		if variant_of:
			specification = frappe.db.sql("select specification, value from `tabItem Quality Inspection Parameter` \
				where parent in (%s, %s) order by idx", (self.item_code, variant_of))
		else:
			specification = frappe.db.sql("select specification, value from `tabItem Quality Inspection Parameter` \
				where parent = %s order by idx", self.item_code)
		for d in specification:
			child = self.append('readings', {})
			child.specification = d[0]
			child.value = d[1]
			child.status = 'Accepted'

	def on_submit(self):
		if self.purchase_receipt_no:
			frappe.db.sql("""update `tabPurchase Receipt Item` t1, `tabPurchase Receipt` t2
				set t1.qa_no = %s, t2.modified = %s
				where t1.parent = %s and t1.item_code = %s and t1.parent = t2.name""",
				(self.name, self.modified, self.purchase_receipt_no, self.item_code))

	def on_cancel(self):
		if self.purchase_receipt_no:
			frappe.db.sql("""update `tabPurchase Receipt Item` set qa_no = '', modified=%s 
				where qa_no = %s""", (self.modified, self.name))

def item_query(doctype, txt, searchfield, start, page_len, filters):
	if filters.get("from"):
		from frappe.desk.reportview import get_match_cond
		filters.update({
			"txt": txt,
			"mcond": get_match_cond(filters["from"]),
			"start": start,
			"page_len": page_len
		})
		return frappe.db.sql("""select item_code from `tab%(from)s`
			where parent='%(parent)s' and docstatus < 2 and item_code like '%%%(txt)s%%' %(mcond)s
			order by item_code limit %(start)s, %(page_len)s""" % filters)
