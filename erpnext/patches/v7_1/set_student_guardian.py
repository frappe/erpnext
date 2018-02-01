import frappe

def execute():
	if frappe.db.exists("DocType", "Guardian"):

		# 'Schools' module changed to the 'Education'
		# frappe.reload_doc("schools", "doctype", "student")
		# frappe.reload_doc("schools", "doctype", "student_guardian")
		# frappe.reload_doc("schools", "doctype", "student_sibling")

		frappe.reload_doc("education", "doctype", "student")
		frappe.reload_doc("education", "doctype", "student_guardian")
		frappe.reload_doc("education", "doctype", "student_sibling")
		if "student" not in frappe.db.get_table_columns("Guardian"):
			return
		guardian = frappe.get_all("Guardian", fields=["name", "student"])
		for d in guardian:
			if d.student:
				student = frappe.get_doc("Student", d.student)
				if student:
					student.append("guardians", {"guardian": d.name})
					student.save()
