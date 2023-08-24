# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AssetActivity(Document):
	pass


def add_asset_activity(asset, subject):
	frappe.get_doc(
		{
			"doctype": "Asset Activity",
			"asset": asset,
			"subject": subject,
			"user": frappe.session.user,
		}
	).insert(ignore_permissions=True, ignore_links=True)
