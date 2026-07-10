frappe.ui.form.on("Product Configuration", {
	refresh(frm) {
		const calculate = frm.add_custom_button(__("Calculate"), () => {
			frm.call("calculate_components").then(() => {
				frm.refresh_field("components");
				frm.dirty();
			});
		});
		if (frm.doc.status === "Draft") {
			calculate.addClass("btn-primary");
		}
		if (frm.doc.status === "Calculated" && !frm.is_dirty()) {
			frm.add_custom_button(__("Create BOM"), () => {
				frm.call("create_bom").then(({ message }) => {
					frappe.set_route("Form", "BOM", message);
				});
			}).addClass("btn-primary");
		}
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
