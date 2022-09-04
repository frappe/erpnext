# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from frappe import _


def get_data():
	return {
		"fieldname": "course",
		"transactions": [
			{
				"label": _("Program and Course"),
				"items": ["Program", "Course Enrollment", "Course Schedule"],
			},
			{"label": _("Student"), "items": ["Student Group"]},
			{"label": _("Assessment"), "items": ["Assessment Plan", "Assessment Result"]},
		],
	}
