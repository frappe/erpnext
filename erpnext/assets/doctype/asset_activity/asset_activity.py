# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class AssetActivity(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		asset: DF.Link
		date: DF.Datetime
		subject: DF.TextEditor
		user: DF.Link
	# end: auto-generated types

	pass


def add_asset_activity(asset, subject):
	frappe.get_doc(
		{
			"doctype": "Asset Activity",
			"asset": asset,
			"subject": subject,
			"user": frappe.session.user,
			"date": now_datetime(),
		}
	).insert(ignore_permissions=True, ignore_links=True)


def get_permission_query_conditions(user: str | None = None, doctype: str | None = None):
	"""Apply the user's restrictions on Asset (user permissions, query conditions) to its activity."""
	user = user or frappe.session.user
	if user == "Administrator" or not frappe.has_permission("Asset", "select", user=user):
		return None

	readable_assets = frappe.qb.get_query("Asset", fields=["name"], ignore_permissions=False, user=user)
	return frappe.qb.DocType("Asset Activity").asset.isin(readable_assets)
