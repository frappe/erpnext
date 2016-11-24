# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import frappe
import frappe.permissions
from erpnext.controllers.recurring_document import date_field_map
from frappe.utils import get_first_day, get_last_day, add_to_date, nowdate, getdate, add_days

def test_recurring_document(obj, test_records):
	frappe.db.set_value("Print Settings", "Print Settings", "send_print_as_pdf", 1)
	today = nowdate()
	base_doc = frappe.copy_doc(test_records[0])

	base_doc.update({
		"is_recurring": 1,
		"submit_on_create": 1,
		"recurring_type": "Monthly",
		"notification_email_address": "test@example.com, test1@example.com, test2@example.com",
		"repeat_on_day_of_month": getdate(today).day,
		"due_date": None,
		"from_date": get_first_day(today),
		"to_date": get_last_day(today)
	})

	date_field = date_field_map[base_doc.doctype]
	base_doc.set(date_field, today)

	if base_doc.doctype == "Sales Order":
		base_doc.set("delivery_date", add_days(today, 15))

	# monthly
	doc1 = frappe.copy_doc(base_doc)
	doc1.insert()
	doc1.submit()
	_test_recurring_document(obj, doc1, date_field, True)

	# monthly without a first and last day period
	if getdate(today).day != 1:
		doc2 = frappe.copy_doc(base_doc)
		doc2.update({
			"from_date": today,
			"to_date": add_to_date(today, days=30)
		})
		doc2.insert()
		doc2.submit()
		_test_recurring_document(obj, doc2, date_field, False)

	# quarterly
	doc3 = frappe.copy_doc(base_doc)
	doc3.update({
		"recurring_type": "Quarterly",
		"from_date": get_first_day(today),
		"to_date": get_last_day(add_to_date(today, months=3))
	})
	doc3.insert()
	doc3.submit()
	_test_recurring_document(obj, doc3, date_field, True)

	# quarterly without a first and last day period
	doc4 = frappe.copy_doc(base_doc)
	doc4.update({
		"recurring_type": "Quarterly",
		"from_date": today,
		"to_date": add_to_date(today, months=3)
	})
	doc4.insert()
	doc4.submit()
	_test_recurring_document(obj, doc4, date_field, False)

	# yearly
	doc5 = frappe.copy_doc(base_doc)
	doc5.update({
		"recurring_type": "Yearly",
		"from_date": get_first_day(today),
		"to_date": get_last_day(add_to_date(today, years=1))
	})
	doc5.insert()
	doc5.submit()
	_test_recurring_document(obj, doc5, date_field, True)

	# yearly without a first and last day period
	doc6 = frappe.copy_doc(base_doc)
	doc6.update({
		"recurring_type": "Yearly",
		"from_date": today,
		"to_date": add_to_date(today, years=1)
	})
	doc6.insert()
	doc6.submit()
	_test_recurring_document(obj, doc6, date_field, False)

	# change date field but keep recurring day to be today
	doc7 = frappe.copy_doc(base_doc)
	doc7.update({
		date_field: today,
	})
	doc7.insert()
	doc7.submit()

	# setting so that _test function works
	# doc7.set(date_field, today)
	_test_recurring_document(obj, doc7, date_field, True)

def _test_recurring_document(obj, base_doc, date_field, first_and_last_day):
	from frappe.utils import add_months, get_last_day
	from erpnext.controllers.recurring_document import manage_recurring_documents, \
		get_next_date

	no_of_months = ({"Monthly": 1, "Quarterly": 3, "Yearly": 12})[base_doc.recurring_type]

	def _test(i):
		obj.assertEquals(i+1, frappe.db.sql("""select count(*) from `tab%s`
			where recurring_id=%s and (docstatus=1 or docstatus=0)""" % (base_doc.doctype, '%s'),
			(base_doc.recurring_id))[0][0])

		next_date = get_next_date(base_doc.get(date_field), no_of_months,
			base_doc.repeat_on_day_of_month)

		manage_recurring_documents(base_doc.doctype, next_date=next_date, commit=False)

		recurred_documents = frappe.db.sql("""select name from `tab%s`
			where recurring_id=%s and (docstatus=1 or docstatus=0) order by name desc"""
			% (base_doc.doctype, '%s'), (base_doc.recurring_id))

		obj.assertEquals(i+2, len(recurred_documents))

		new_doc = frappe.get_doc(base_doc.doctype, recurred_documents[0][0])

		for fieldname in ["is_recurring", "recurring_type",
			"repeat_on_day_of_month", "notification_email_address"]:
				obj.assertEquals(base_doc.get(fieldname),
					new_doc.get(fieldname))

		obj.assertEquals(new_doc.get(date_field), getdate(next_date))

		obj.assertEquals(new_doc.from_date,	getdate(add_months(base_doc.from_date, no_of_months)))

		if first_and_last_day:
			obj.assertEquals(new_doc.to_date, getdate(get_last_day(add_months(base_doc.to_date, no_of_months))))
		else:
			obj.assertEquals(new_doc.to_date, getdate(add_months(base_doc.to_date, no_of_months)))

		return new_doc

	# if yearly, test 1 repetition, else test 5 repetitions
	count = 1 if (no_of_months == 12) else 5
	for i in xrange(count):
		base_doc = _test(i)
