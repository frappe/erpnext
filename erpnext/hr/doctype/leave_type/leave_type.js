frappe.ui.form.on("Leave Type", {
	refresh: function(frm) {
		frm.add_custom_button(__("Allocations"), function() {
			frappe.set_route("List", "Leave Allocation",
			{"leave_type": frm.doc.name});
		});
	}
});
