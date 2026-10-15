# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Snapshot the old editable balances before Shareholder's schema is replaced."""

import frappe
from frappe.query_builder.functions import Coalesce


def execute():
	if not frappe.db.table_exists("Share Balance", cached=False):
		return

	create_staging_table()

	source = frappe.qb.DocType("Share Balance")
	staging = frappe.qb.DocType("Shareholding Legacy Balance Staging")
	existing = frappe.qb.from_(staging).select(staging.name)
	(
		frappe.qb.into(staging)
		.columns("name", "parent", "share_type", "from_no", "to_no", "no_of_shares", "is_company")
		.from_(source)
		.select(
			source.name,
			source.parent,
			source.share_type,
			source.from_no,
			source.to_no,
			source.no_of_shares,
			Coalesce(source.is_company, 0),
		)
		.where((source.parenttype == "Shareholder") & source.name.notin(existing))
	).run()


def create_staging_table():
	frappe.db.multisql(
		{
			"mariadb": """
		create table if not exists `tabShareholding Legacy Balance Staging` (
			`name` varchar(140) not null primary key,
			`parent` varchar(140) not null,
			`share_type` varchar(140),
			`from_no` int,
			`to_no` int,
			`no_of_shares` int,
			`is_company` int not null default 0
		)
		""",
			"postgres": """
		create table if not exists "tabShareholding Legacy Balance Staging" (
			"name" varchar(140) not null primary key,
			"parent" varchar(140) not null,
			"share_type" varchar(140),
			"from_no" int,
			"to_no" int,
			"no_of_shares" int,
			"is_company" int not null default 0
		)
		""",
		}
	)
