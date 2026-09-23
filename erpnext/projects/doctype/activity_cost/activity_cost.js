frappe.ui.form.on("Activity Cost", {
	setup: function (frm) {
		frm.add_fetch("employee", "employee_name", "employee_name");
	},
});
