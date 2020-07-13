# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class ParcelServiceType(Document):
	pass

def match_parcel_service_type_alias(parcel_service_type, parcel_service):
	# Match and return Parcel Service Type Alias to Parcel Service Type if exists.
	if frappe.db.exists('Parcel Service', parcel_service):
		matched_parcel_service_type = \
			frappe.db.get_value('Parcel Service Type Alias', {
				'parcel_type_alias': parcel_service_type,
				'parcel_service': parcel_service
			}, 'parent')
		if matched_parcel_service_type:
			parcel_service_type = matched_parcel_service_type
	return parcel_service_type
