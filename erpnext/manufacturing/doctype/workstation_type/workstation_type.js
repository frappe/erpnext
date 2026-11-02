// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Workstation Type", {
	refresh(frm) {
		if (["Filling Line", "Bagging Line"].includes(frm.doc.machine_model)) return;

		if (!frm.is_new()) {
			frm.add_custom_button(__("Open Designer"), () => frm.events.open_designer(frm), __("3D Model"));
		}
		frm.add_custom_button(
			__("Copy Preset Shapes"),
			() => frm.events.copy_preset_shapes(frm),
			__("3D Model")
		);
	},

	async open_designer(frm) {
		if (frm.is_dirty()) await frm.save();
		frappe.set_route("plant-builder", "machine", frm.doc.name, "design");
	},

	copy_preset_shapes(frm) {
		const copy = () => frm.call("copy_preset_shapes").then(() => frm.dirty());
		if (!frm.doc.shapes?.length) return copy();

		const preset = frm.doc.machine_model || __("Machine");
		frappe.confirm(__("Replace the shapes with the {0} preset?", [preset]), copy);
	},
});
