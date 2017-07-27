# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.db.sql("update tabItem set has_batch_no = 0 where ifnull(has_batch_no, '') = ''")
	frappe.db.sql("update tabItem set has_serial_no = 0 where ifnull(has_serial_no, '') = ''")

	item_list = frappe.db.sql("""select name, has_batch_no, has_serial_no from tabItem
		where is_stock_item = 1""", as_dict=1)

	sle_count = get_sle_count()
	sle_with_batch = get_sle_with_batch()
	sle_with_serial = get_sle_with_serial()

	batch_items = get_items_with_batch()
	serialized_items = get_items_with_serial()

	for d in item_list:
		if d.has_batch_no == 1:
			if d.name not in batch_items and sle_count.get(d.name) and sle_count.get(d.name) != sle_with_batch.get(d.name):
					frappe.db.set_value("Item", d.name, "has_batch_no", 0)
		else:
			if d.name in batch_items or (sle_count.get(d.name) and sle_count.get(d.name) == sle_with_batch.get(d.name)):
				frappe.db.set_value("Item", d.name, "has_batch_no", 1)

		if d.has_serial_no == 1:
			if d.name not in serialized_items and sle_count.get(d.name) and sle_count.get(d.name) != sle_with_serial.get(d.name):
				frappe.db.set_value("Item", d.name, "has_serial_no", 0)
		else:
			if d.name in serialized_items or (sle_count.get(d.name) and sle_count.get(d.name) == sle_with_serial.get(d.name)):
				frappe.db.set_value("Item", d.name, "has_serial_no", 1)


def get_sle_count():
	sle_count = {}
	for d in frappe.db.sql("""select item_code, count(name) as cnt from `tabStock Ledger Entry` group by item_code""", as_dict=1):
		sle_count.setdefault(d.item_code, d.cnt)

	return sle_count

def get_sle_with_batch():
	sle_with_batch = {}
	for d in frappe.db.sql("""select item_code, count(name) as cnt from `tabStock Ledger Entry`
		where ifnull(batch_no, '') != '' group by item_code""", as_dict=1):
			sle_with_batch.setdefault(d.item_code, d.cnt)

	return sle_with_batch


def get_sle_with_serial():
	sle_with_serial = {}
	for d in frappe.db.sql("""select item_code, count(name) as cnt from `tabStock Ledger Entry`
		where ifnull(serial_no, '') != '' group by item_code""", as_dict=1):
			sle_with_serial.setdefault(d.item_code, d.cnt)

	return sle_with_serial

def get_items_with_batch():
	return frappe.db.sql_list("select item from tabBatch")

def get_items_with_serial():
	return frappe.db.sql_list("select item_code from `tabSerial No`")
