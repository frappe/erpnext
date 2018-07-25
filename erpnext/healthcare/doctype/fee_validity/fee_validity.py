# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
import frappe
from frappe.utils import getdate
import datetime

class FeeValidity(Document):
	pass

def update_fee_validity(fee_validity, date, ref_invoice=None):
	max_visit = frappe.db.get_value("Healthcare Settings", None, "max_visit")
	valid_days = frappe.db.get_value("Healthcare Settings", None, "valid_days")
	if not valid_days:
		valid_days = 1
	if not max_visit:
		max_visit = 1
	date = getdate(date)
	valid_till = date + datetime.timedelta(days=int(valid_days))
	fee_validity.max_visit = max_visit
	fee_validity.visited = 1
	fee_validity.valid_till = valid_till
	fee_validity.ref_invoice = ref_invoice
	fee_validity.save(ignore_permissions=True)
	return fee_validity


def create_fee_validity(practitioner, patient, date, ref_invoice=None):
	fee_validity = frappe.new_doc("Fee Validity")
	fee_validity.practitioner = practitioner
	fee_validity.patient = patient
	fee_validity = update_fee_validity(fee_validity, date, ref_invoice)
	return fee_validity
