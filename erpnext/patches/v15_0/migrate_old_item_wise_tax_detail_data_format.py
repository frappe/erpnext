import json

import frappe
from frappe.utils import flt

from erpnext.controllers.taxes_and_totals import ItemWiseTaxDetail


def execute():
	# Get all DocTypes that have the 'item_wise_tax_detail' field
	doctypes_with_tax_details = frappe.get_all(
		"DocField", filters={"fieldname": "item_wise_tax_detail"}, fields=["parent"], pluck="parent"
	)
	for doctype in doctypes_with_tax_details:
		migrated_count = 0  # Counter for migrated records per DocType
		# Get all documents of this DocType that have data in 'item_wise_tax_detail'
		docs = frappe.get_all(
			doctype,
			filters={"item_wise_tax_detail": ["is", "set"]},
			fields=["name", "item_wise_tax_detail"],
		)
		for doc in docs:
			if not doc.item_wise_tax_detail:
				continue

			updated_tax_details = {}
			needs_update = False

			try:
				item_iterator = json.loads(doc.item_wise_tax_detail).items()
			except AttributeError as e:
				# This is stale data from 2009 found in a database
				if isinstance(json.loads(doc.item_wise_tax_detail), int | float):
					needs_update = False
				else:
					raise e
			else:
				for item, tax_data in item_iterator:
					if isinstance(tax_data, list) and len(tax_data) == 2:
						updated_tax_details[item] = ItemWiseTaxDetail(
							tax_rate=tax_data[0],
							tax_amount=tax_data[1],
							# can't be reliably reconstructed since it depends on the tax type
							# (actual, net, previous line total, previous line net, etc)
							net_amount=0.0,
						)
						needs_update = True
					# intermediate patch version of the originating PR
					elif isinstance(tax_data, list) and len(tax_data) == 3:
						updated_tax_details[item] = ItemWiseTaxDetail(
							tax_rate=tax_data[0],
							tax_amount=tax_data[1],
							net_amount=tax_data[2],
						)
						needs_update = True
					elif isinstance(tax_data, str):
						updated_tax_details[item] = ItemWiseTaxDetail(
							tax_rate=flt(tax_data),
							tax_amount=0.0,
							net_amount=0.0,
						)
						needs_update = True
					else:
						updated_tax_details[item] = tax_data

			if needs_update:
				frappe.db.set_value(
					doctype,
					doc.name,
					"item_wise_tax_detail",
					json.dumps(updated_tax_details),
					update_modified=False,
				)
				migrated_count += 1  # Increment the counter for each migrated record

		frappe.db.commit()
		print(f"Migrated {migrated_count} records for DocType: {doctype}")
