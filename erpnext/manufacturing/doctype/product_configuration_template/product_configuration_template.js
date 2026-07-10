frappe.ui.form.on("Product Configuration Template", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}
		frm.add_custom_button(__("Configure"), () => open_configure_dialog(frm));
		frm.add_custom_button(__("New Rule"), () => {
			frappe.new_doc("Product Configuration Rule", { template: frm.doc.name });
		});
	},
});

function open_configure_dialog(frm) {
	frm.call("get_attribute_fields").then(({ message: fields }) => {
		const dialog = new frappe.ui.Dialog({
			title: __("Configure {0}", [frm.doc.name]),
			fields: fields,
			primary_action_label: __("Create Configuration"),
			primary_action(values) {
				dialog.hide();
				frm.call("make_configuration", { values }).then(({ message: name }) => {
					frappe.set_route("Form", "Product Configuration", name);
				});
			},
		});
		dialog.show();
	});
}
