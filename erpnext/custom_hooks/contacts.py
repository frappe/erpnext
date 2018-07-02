#!/bin/env python
# -*- coding: utf-8 -*-

"""Update issue."""
import frappe


def update_issue(contact, method):
	"""Update tabIssue"""
	frappe.db.sql("""update `tabIssue` set contact='' where contact=%s""",	
-			contact.name)
