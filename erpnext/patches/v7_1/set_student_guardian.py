import frappe

def execute():
	if frappe.db.exists("DocType", "Guardian"):
		frappe.reload_doc("schools", "doctype", "student")
		frappe.reload_doc("schools", "doctype", "student_guardian")
		guardian = frappe.get_list("Guardian", fields=["name", "student"])
		for d in guardian:
			if d.student:
				student = frappe.get_doc("Student", d.student)
				if student:
					student.append("guardians", {"guardian": d.name})
					student.save()