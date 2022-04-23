# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import frappe
from frappe import session, _
from frappe.utils import today, now_datetime



from erpnext.utilities.transaction_base import TransactionBase

class WarrantyClaim(TransactionBase):
	def get_feed(self):
		return _("{0}: From {1}").format(self.status, self.customer_name)

	def validate(self):
		if session['user'] != 'Guest' and not self.customer:
			frappe.throw(_("Customer is required"))

		if self.status=="Closed" and not self.resolution_date and \
			frappe.db.get_value("Warranty Claim", self.name, "status")!="Closed":
			self.resolution_date = now_datetime()

	def on_cancel(self):
		lst = frappe.db.sql("""select t1.name
			from `tabMaintenance Visit` t1, `tabMaintenance Visit Purpose` t2
			where t2.parent = t1.name and t2.prevdoc_docname = %s and	t1.docstatus!=2""",
			(self.name))
		if lst:
			lst1 = ','.join(x[0] for x in lst)
			frappe.throw(_("Cancel Material Visit {0} before cancelling this Warranty Claim").format(lst1))
		else:
			frappe.db.set(self, 'status', 'Cancelled')

	def on_update(self):
		pass

@frappe.whitelist()
def make_maintenance_visit(source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc, map_child_doc

	def _update_links(source_doc, target_doc, source_parent):
		target_doc.prevdoc_doctype = source_parent.doctype
		target_doc.prevdoc_docname = source_parent.name

	visit = frappe.db.sql("""select t1.name
		from `tabMaintenance Visit` t1, `tabMaintenance Visit Purpose` t2
		where t2.parent=t1.name and t2.prevdoc_docname=%s
		and t1.docstatus=1 and t1.completion_status='Fully Completed'""", source_name)

	if not visit:
		target_doc = get_mapped_doc("Warranty Claim", source_name, {
			"Warranty Claim": {
				"doctype": "Maintenance Visit",
				"field_map": {}
			}
		}, target_doc)

		source_doc = frappe.get_doc("Warranty Claim", source_name)
		if source_doc.get("item_code"):
			table_map = {
				"doctype": "Maintenance Visit Purpose",
				"postprocess": _update_links
			}
			map_child_doc(source_doc, target_doc, table_map, source_doc)

		return target_doc
