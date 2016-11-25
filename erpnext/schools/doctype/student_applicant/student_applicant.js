frappe.ui.form.on("Student Applicant", {
	refresh: function(frm) {
		if(frm.doc.application_status== "Applied" && frm.doc.docstatus== 1 ) {
			frm.add_custom_button(__("Approve"), function() {
				frm.set_value("application_status", "Approved");
				frm.save_or_update();

			}, 'Actions');

			frm.add_custom_button(__("Reject"), function() {
				frm.set_value("application_status", "Rejected");
				frm.save_or_update();
			}, 'Actions');
		}

		if(frm.doc.application_status== "Approved" && frm.doc.docstatus== 1 ) {
			frm.add_custom_button(__("Enroll"), function() {
				frm.events.enroll(frm)
			}).addClass("btn-primary");
		}
	},

	enroll: function(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.schools.api.enroll_student",
			frm: frm
		})
	}
});