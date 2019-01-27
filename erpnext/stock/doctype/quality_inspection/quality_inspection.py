# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnext.stock.doctype.quality_inspection_template.quality_inspection_template \
	import get_template_details

class QualityInspection(Document):
	def validate(self):
		if not self.readings and self.item_code:
			self.get_item_specification_details()

	def get_item_specification_details(self):
		if not self.quality_inspection_template:
			self.quality_inspection_template = frappe.db.get_value('Item',
				self.item_code, 'quality_inspection_template')

		if not self.quality_inspection_template: return

		self.set('readings', [])
		parameters = get_template_details(self.quality_inspection_template)
		for d in parameters:
			child = self.append('readings', {})
			child.specification = d.specification
			child.value = d.value
			child.status = "Accepted"

	def get_quality_inspection_template(self):
		template = ''
		if self.bom_no:
			template = frappe.db.get_value('BOM', self.bom_no, 'quality_inspection_template')

		if not template:
			template = frappe.db.get_value('BOM', self.item_code, 'quality_inspection_template')

		self.quality_inspection_template = template
		self.get_item_specification_details()

	def on_submit(self):
		self.update_qc_reference()

	def on_cancel(self):
		self.update_qc_reference()

	def update_qc_reference(self):
		quality_inspection = self.name if self.docstatus == 1 else ""
		doctype = self.reference_type + ' Item'
		if self.reference_type == 'Stock Entry':
			doctype = 'Stock Entry Detail'

		if self.reference_type and self.reference_name:
			frappe.db.sql("""update `tab{child_doc}` t1, `tab{parent_doc}` t2
				set t1.quality_inspection = %s, t2.modified = %s
				where t1.parent = %s and t1.item_code = %s and t1.parent = t2.name"""
				.format(parent_doc=self.reference_type, child_doc=doctype),
				(quality_inspection, self.modified, self.reference_name, self.item_code))

def item_query(doctype, txt, searchfield, start, page_len, filters):
	if filters.get("from"):
		from frappe.desk.reportview import get_match_cond
		mcond = get_match_cond(filters["from"])
		cond, qi_condition = "", "and (quality_inspection is null or quality_inspection = '')"

		if filters.get('from') in ['Purchase Invoice Item', 'Purchase Receipt Item']:
			cond = """and item_code in (select name from `tabItem` where
				inspection_required_before_purchase = 1)"""
		elif filters.get('from') in ['Sales Invoice Item', 'Delivery Note Item']:
			cond = """and item_code in (select name from `tabItem` where
				inspection_required_before_delivery = 1)"""
		elif filters.get('from') == 'Stock Entry Detail':
			cond = """and s_warehouse is null"""

		if filters.get('from') in ['Supplier Quotation Item']:
			qi_condition = ""

		return frappe.db.sql(""" select item_code from `tab{doc}`
			where parent=%(parent)s and docstatus < 2 and item_code like %(txt)s
			{qi_condition} {cond} {mcond}
			order by item_code limit {start}, {page_len}""".format(doc=filters.get('from'),
			parent=filters.get('parent'), cond = cond, mcond = mcond, start = start,
			page_len = page_len, qi_condition = qi_condition),
			{'parent': filters.get('parent'), 'txt': "%%%s%%" % txt})
