from __future__ import unicode_literals
import frappe

from frappe import _

def setup_agriculture():
	records = [
		dict(doctype="Land Unit", land_unit_name="All Land Units", is_group=1, is_container=1),
		dict(doctype='Item Group', item_group_name='Fertilizer', is_group=0, parent_item_group='All Item Groups'),
		dict(doctype='Item Group', item_group_name='Seed', is_group=0, parent_item_group='All Item Groups'),
		dict(doctype='Item Group', item_group_name='By-product', is_group=0, parent_item_group='All Item Groups'),
		dict(doctype='Item Group', item_group_name='Produce', is_group=0, parent_item_group='All Item Groups')
	] 
	insert_record(records)

def insert_record(records):
	for r in records:
		doc = frappe.new_doc(r.get("doctype"))
		doc.update(r)
		try:
			doc.insert(ignore_permissions=True)
			print('In agriculture setup')
		except frappe.DuplicateEntryError, e:
			# pass DuplicateEntryError and continue
			if e.args and e.args[0]==doc.doctype and e.args[1]==doc.name:
				# make sure DuplicateEntryError is for the exact same doc and not a related doc
				pass
			else:
				raise