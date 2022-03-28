# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from frappe import _


def get_data():
	return {
		"reports": [
			{"label": _("Reports"), "items": ["Final Assessment Grades", "Course wise Assessment Report"]}
		]
	}
