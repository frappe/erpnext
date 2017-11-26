// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Soil Analysis', {
	refresh: (frm) => {
		let map_tools = ["a.leaflet-draw-draw-polyline",
			"a.leaflet-draw-draw-polygon",
			"a.leaflet-draw-draw-rectangle",
			"a.leaflet-draw-draw-circle",
			"a.leaflet-draw-draw-circlemarker"];

		map_tools.forEach((element) => $(element).hide());
	}
});
