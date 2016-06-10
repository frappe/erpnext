frappe.ui.form.on("Issue", {
	"onload": function(frm) {
		frm.email_field = "raised_by";
	},

	"refresh": function(frm) {
		if(frm.doc.status==="Open") {
			frm.add_custom_button(__("Close"), function() {
				frm.set_value("status", "Closed");
				frm.save();
			});
		} else {
			frm.add_custom_button(__("Reopen"), function() {
				frm.set_value("status", "Open");
				frm.save();
			});
		}
	}
});
