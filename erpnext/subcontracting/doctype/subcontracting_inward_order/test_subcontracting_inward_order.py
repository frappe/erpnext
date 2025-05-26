# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from erpnext.selling.doctype.sales_order.sales_order import get_mapped_subcontracting_inward_order

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class UnitTestSubcontractingInwardOrder(UnitTestCase):
	"""
	Unit tests for SubcontractingInwardOrder.
	Use this class for testing individual functions and methods.
	"""

	pass


class IntegrationTestSubcontractingInwardOrder(IntegrationTestCase):
	"""
	Integration tests for SubcontractingInwardOrder.
	Use this class for testing interactions between multiple components.
	"""

	pass


def create_subcontracting_inward_order(**args):
	args = frappe._dict(args)
	scio = get_mapped_subcontracting_inward_order(source_name=args.so_name)

	scio.raw_materials_receipt_Warehouse = args.raw_materials_receipt_warehouse

	for item in scio.items:
		item.include_exploded_items = args.get("include_exploded_items", 1)

	if args.warehouse:
		for item in scio.items:
			item.warehouse = args.warehouse
	else:
		warehouse = frappe.get_value("Sales Order", args.so_name, "set_warehouse")
		if warehouse:
			for item in scio.items:
				item.warehouse = warehouse
		else:
			so = frappe.get_doc("Sales Order", args.so_name)
			warehouses = []
			for item in so.items:
				warehouses.append(item.warehouse)
			else:
				for idx, val in enumerate(scio.items):
					val.warehouse = warehouses[idx]

	warehouses = set()
	for item in scio.items:
		warehouses.add(item.warehouse)

	if len(warehouses) == 1:
		scio.set_warehouse = next(iter(warehouses))

	if not args.do_not_save:
		scio.insert()
		if not args.do_not_submit:
			scio.submit()

	return scio
