# Copyright (c) 2019

from __future__ import unicode_literals
import frappe

def execute():
	frappe.delete_doc("Page", "medical_record")
