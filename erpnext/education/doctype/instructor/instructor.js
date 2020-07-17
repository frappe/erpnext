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
	}
});