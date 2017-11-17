// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide('agriculture');

frappe.ui.form.on('Soil Texture', {
	onload: function(frm) {
		this.ternary_plot = new agriculture.TernaryPlot({
			parent: frm.get_field("ternary_plot").$wrapper,
			clay: frm.doc.clay_composition,
			sand: frm.doc.sand_composition,
			silt: frm.doc.silt_composition
		});
	},
	clay_composition: function(frm) {
		frm.call("update_soil_edit", {
			soil_type: 'clay_composition'
		}, () => {
			refresh_ternary_plot(frm, this);
		});
	},
	sand_composition: function(frm) {
		frm.call("update_soil_edit", {
			soil_type: 'sand_composition'
		}, () => {
			refresh_ternary_plot(frm, this);
		});
	},
	silt_composition: function(frm) {
		frm.call("update_soil_edit", {
			soil_type: 'silt_composition'
		}, () => {
			refresh_ternary_plot(frm, this);
		});
	}
});

let refresh_ternary_plot = (frm, me) => {
	me.ternary_plot.remove_blip();
	me.ternary_plot.mark_blip({clay: frm.doc.clay_composition, sand: frm.doc.sand_composition, silt: frm.doc.silt_composition});
};
