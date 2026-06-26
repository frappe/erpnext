frappe.ui.form.on("Product Configuration", {
	refresh(frm) {
		frm.add_custom_button(__("Calculate Components"), () => {
			frm.call("calculate_components").then(() => {
				frm.refresh_field("components");
				frm.dirty();
			});
		});
	},

	template(frm) {
		if (!frm.doc.template) {
			return;
		}
		frm.call("fetch_template_attributes").then(() => {
			frm.refresh_field("attribute_values");
		});
	},
});
