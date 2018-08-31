frappe.ui.form.on("Hub Settings", {
	refresh: function(frm) {
		$('#toolbar-user .marketplace-link').toggle(!frm.doc.disable_marketplace);
	},
});
