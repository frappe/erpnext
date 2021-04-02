// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Water Analysis', {
	onload: (frm) => {
		if (frm.doc.water_analysis_criteria == undefined) frm.call('load_contents');
	},
	refresh: (frm) => {
		let map_tools = ["a.leaflet-draw-draw-polyline",
			"a.leaflet-draw-draw-polygon",
			"a.leaflet-draw-draw-rectangle",
			"a.leaflet-draw-draw-circle",
			"a.leaflet-draw-draw-circlemarker"];

		map_tools.forEach((element) => $(element).hide());
	},
	laboratory_testing_datetime: (frm) => frm.call("update_lab_result_date")
});
