// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Plant Floor", {
	refresh(frm) {
		frm.trigger('prepare_dashboard')
	},

	prepare_dashboard(frm) {
		let wrapper = $(frm.fields_dict["plant_dashboard"].wrapper);
		wrapper.empty();

		frappe.visual_plant_floor = new frappe.ui.VisualPlantFloor({
			wrapper: wrapper,
			skip_filters: true,
			plant_floor: frm.doc.name,
		});
	},
});
