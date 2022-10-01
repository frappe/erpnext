# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe


class TestCourseActivity(unittest.TestCase):
	pass


def make_course_activity(enrollment, content_type, content):
	activity = frappe.get_all(
		"Course Activity",
		filters={"enrollment": enrollment, "content_type": content_type, "content": content},
	)
	try:
		activity = frappe.get_doc("Course Activity", activity[0]["name"])
	except (IndexError, frappe.DoesNotExistError):
		activity = frappe.get_doc(
			{
				"doctype": "Course Activity",
				"enrollment": enrollment,
				"content_type": content_type,
				"content": content,
				"activity_date": frappe.utils.datetime.datetime.now(),
			}
		).insert()
	return activity
