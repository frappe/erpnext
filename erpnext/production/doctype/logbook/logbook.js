// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Logbook', {
	// refresh: function(frm) {

	// }
	branch:function(frm){		
		frm.set_query("equipment_hiring_form", function() {
			return {
				filters: {
					branch : frm.doc.branch
				}
			}
		})
	}
});
frappe.ui.form.on("Logbook Item", {
	uom: function(frm, cdt, cdn) {
		calculate_time(frm, cdt, cdn)
	},
	reading_initial: function(frm, cdt, cdn) {
		calculate_time(frm, cdt, cdn)
	},
	reading_final: function(frm, cdt, cdn) {
		calculate_time(frm, cdt, cdn)
	},
	initial_time: function(frm, cdt, cdn) {
		calculate_time(frm, cdt, cdn)
	},
	final_time: function(frm, cdt, cdn) {
		calculate_time(frm, cdt, cdn)
	},
	initial_reading: function(frm, cdt, cdn) {
		calculate_time(frm, cdt, cdn)
	},
	target_trip: function(frm, cdt, cdn) {
		calculate_time(frm, cdt, cdn)
	},
	final_reading: function(frm, cdt, cdn) {
		calculate_time(frm, cdt, cdn)
	},
	idle_time: function(frm, cdt, cdn) {
		calculate_time(frm, cdt, cdn)
	},
})
var calculate_time = function(frm, cdt, cdn) {
	let hour = 0
	let item = locals[cdt][cdn]
	if(item.uom == "Hour") {
		hour = item.reading_final - item.reading_initial - item.idle_time
	}
	else if(item.uom == "Time") {
		let fdate = new Date("October 13, 2014 " + item.final_time)
		let tdate = new Date("October 13, 2014 " + item.initial_time)
		let diff = (fdate.getTime() - tdate.getTime()) / 1000;
		hour = diff / 3600 - item.idle_time;
	}
	else {
		if (item.target_trip) {
			hour = (item.initial_reading/item.target_trip)*frm.doc.target_hours
		}
	}
	frappe.model.set_value(cdt, cdn,"hours", hour)
	cur_frm.refresh_fields()
}