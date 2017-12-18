// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

// Code for finding the area of editable features drawn on the geolocation control



frappe.ui.form.on('Land Unit', {
	setup: function(frm) {
		frm.add_fetch("parent_land_unit", "latitude", "latitude");
		frm.add_fetch("parent_land_unit", "longitude", "longitude");
		frm.set_query("parent_land_unit", function() {
			return {
				"filters": {
					"is_group": 1
				}
			};
		});
	},

	onload_post_render(frm){
		if(!frm.doc.location && frm.doc.latitude && frm.doc.longitude)	{
			frm.fields_dict.location.map.setView([frm.doc.latitude, frm.doc.longitude],13);
		}
		else {
			frm.doc.latitude = frm.fields_dict.location.map.getCenter()['lat'];
			frm.doc.longitude = frm.fields_dict.location.map.getCenter()['lng'];
		}
	},
});
