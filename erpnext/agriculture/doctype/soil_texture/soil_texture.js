// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide('agriculture');

frappe.ui.form.on('Soil Texture', {
	refresh: (frm) => {
		let map_tools = ["a.leaflet-draw-draw-polyline",
			"a.leaflet-draw-draw-polygon",
			"a.leaflet-draw-draw-rectangle",
			"a.leaflet-draw-draw-circle",
			"a.leaflet-draw-draw-circlemarker"];

		map_tools.forEach((element) => $(element).hide());
	},
	onload: function(frm) {
		if (frm.doc.soil_texture_criteria == undefined) frm.call('load_contents');
		if (frm.doc.ternary_plot) return;
		frm.doc.ternary_plot = new agriculture.TernaryPlot({
			parent: frm.get_field("ternary_plot").$wrapper,
			clay: frm.doc.clay_composition,
			sand: frm.doc.sand_composition,
			silt: frm.doc.silt_composition,
		});
	},
	soil_type: (frm) => {
		let composition_types = ['clay_composition', 'sand_composition', 'silt_composition'];
		composition_types.forEach((composition_type) => {
			frm.doc[composition_type] = 0;
			frm.refresh_field(composition_type);
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
