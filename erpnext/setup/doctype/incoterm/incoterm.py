# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Incoterm(Document):
	pass


def create_incoterms():
	"""Create Incoterm records from incoterms.csv."""
	import os
	from csv import DictReader

	with open(os.path.join(os.path.dirname(__file__), "incoterms.csv"), "r") as f:
		for incoterm in DictReader(f):
			if frappe.db.exists("Incoterm", incoterm["code"]):
				continue

			doc = frappe.new_doc("Incoterm")
			doc.update(incoterm)
			doc.save()
