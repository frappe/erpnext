# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate
from frappe.model.document import Document

class AssetActivity(Document):
	def validate(self):
		from assets.controllers.base_asset import validate_serial_no

		self.validate_activity_date()
		validate_serial_no(self)

	def validate_activity_date(self):
		purchase_date = frappe.db.get_value('Asset', self.asset, 'purchase_date')

		if getdate(self.activity_date) < purchase_date:
			frappe.throw(_('Asset Activity cannot be performed before {0}').format(purchase_date))

def create_asset_activity(asset, activity_type, reference_doctype, reference_docname, activity_date=None, asset_serial_no=None, notes=None):
	if not activity_date:
		activity_date = getdate()

	asset_activity = frappe.get_doc({
		'doctype': 'Asset Activity',
		'asset': asset,
		'serial_no': asset_serial_no,
		'activity_date': activity_date,
		'activity_type': activity_type,
		'reference_doctype': reference_doctype,
		'reference_docname': reference_docname,
		'notes': notes
	})
	asset_activity.submit()
