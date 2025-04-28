# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
<<<<<<< HEAD
from frappe.tests import IntegrationTestCase


class TestWorkstationType(IntegrationTestCase):
=======
from frappe.tests.utils import FrappeTestCase


class TestWorkstationType(FrappeTestCase):
>>>>>>> 7c4cf3e834 (Favicon.svg)
	pass


def create_workstation_type(**args):
	args = frappe._dict(args)

	if workstation_type := frappe.db.exists("Workstation Type", args.workstation_type):
		return frappe.get_doc("Workstation Type", workstation_type)
	else:
		doc = frappe.new_doc("Workstation Type")
		doc.update(args)
		doc.insert()
		return doc
