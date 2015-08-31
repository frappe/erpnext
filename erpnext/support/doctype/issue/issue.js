frappe.ui.form.on("Issue", {
	"refresh": function(frm) {
		if(frm.doc.status==="Open") {
			frm.add_custom_button("Close", function() {
				frm.set_value("status", "Closed");
				frm.save();
			});
		} else {
			frm.add_custom_button("Reopen", function() {
				frm.set_value("status", "Open");
				frm.save();
			});
		}
	}
});
