# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from frappe.model.document import Document


class EmployeeEducation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		class_per: DF.Data | None
		level: DF.Literal["Graduate", "Post Graduate", "Under Graduate"]
		maj_opt_subj: DF.Text | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		qualification: DF.Data | None
		school_univ: DF.SmallText | None
		year_of_passing: DF.Int
	# end: auto-generated types

	pass
