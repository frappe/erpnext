cur_frm.add_fetch("employee", "department", "department");
cur_frm.add_fetch("employee", "image", "image");

frappe.ui.form.on("Instructor", {
	employee: function(frm) {
		if (!frm.doc.employee) return;
		frappe.db.get_value("Employee", {name: frm.doc.employee}, "company", (d) => {
			frm.set_query("department", function() {
				return {
					"filters": {
						"company": d.company,
					}
				};
			});
			frm.set_query("department", "instructor_log", function() {
				return {
					"filters": {
						"company": d.company,
					}
				};
			});
		});
	},
	refresh: function(frm) {
		if (!frm.doc.__islocal) {
			frm.add_custom_button(__("As Examiner"), function() {
				frappe.new_doc("Assessment Plan", {
					examiner: frm.doc.name
				});
			}, __("Assessment Plan"));
			frm.add_custom_button(__("As Supervisor"), function() {
				frappe.new_doc("Assessment Plan", {
					supervisor: frm.doc.name
				});
			}, __("Assessment Plan"));
		}
		frm.set_query("employee", function(doc) {
			return {
				"filters": {
					"department": doc.department,
				}
			};
		});

		frm.set_query("academic_term", "instructor_log", function(_doc, cdt, cdn) {
			let d = locals[cdt][cdn];
			return {
				filters: {
					"academic_year": d.academic_year
				}
			};
		});

		frm.set_query("course", "instructor_log", function(_doc, cdt, cdn) {
			let d = locals[cdt][cdn];
			return {
				query: "erpnext.education.doctype.program_enrollment.program_enrollment.get_program_courses",
				filters: {
					"program": d.program
				}
			};
		});
	}
});