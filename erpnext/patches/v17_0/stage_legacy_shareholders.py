# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Preserve old Accounts Shareholder fields before the new DocType schema is synced.

The staging table is deliberately retained after migration so an administrator
can audit the original company and folio identifiers if manual review is needed.
"""

import frappe
from frappe.query_builder.functions import Coalesce


def execute():
	legacy_fields = ("title", "company", "folio_no", "is_company")
	if not all(frappe.db.has_column("Shareholder", fieldname) for fieldname in legacy_fields):
		return

	create_staging_table()

	source = frappe.qb.DocType("Shareholder")
	staging = frappe.qb.DocType("Shareholding Legacy Staging")
	existing = frappe.qb.from_(staging).select(staging.name)
	(
		frappe.qb.into(staging)
		.columns("name", "title", "company", "folio_no", "is_company")
		.from_(source)
		.select(source.name, source.title, source.company, source.folio_no, Coalesce(source.is_company, 0))
		.where(source.name.notin(existing))
	).run()


def create_staging_table():
	frappe.db.multisql(
		{
			"mariadb": """
		create table if not exists `tabShareholding Legacy Staging` (
			`name` varchar(140) not null primary key,
			`title` varchar(140),
			`company` varchar(140),
			`folio_no` varchar(140),
			`is_company` int not null default 0
		)
		""",
			"postgres": """
		create table if not exists "tabShareholding Legacy Staging" (
			"name" varchar(140) not null primary key,
			"title" varchar(140),
			"company" varchar(140),
			"folio_no" varchar(140),
			"is_company" int not null default 0
		)
		""",
		}
	)
