// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Fleet Engagement', {
	refresh: function(frm) {
		frm.set_query('equipment', 'items', function (doc, cdt, cdn) {
			return {
				filters: {
					"hired_equipment": 0,
					// "branch":frm.doc.branch
				}
			}
		});
	},
	branch:function(frm){
		frm.set_query('equipment', 'items', function (doc, cdt, cdn) {
			return {
				filters: {
					"hired_equipment": 0,
					// "branch":frm.doc.branch
				}
			}
		});
	}
});

frappe.ui.form.on('Fleet Engagement Item', {
	initial_km:function(frm,cdt,cdn){
		calculate_total_km(frm,cdt,cdn)
	},
	final_km:function(frm,cdt,cdn){
		calculate_total_km(frm,cdt,cdn)
	},
	start_time:function(frm,cdt,cdn){
		calculate_total_time(frm,cdt,cdn)
	},
	end_time:function(frm,cdt,cdn){
		calculate_total_time(frm,cdt,cdn)
	},
})

var calculate_total_km = function(frm, cdt, cdn){
	let item = locals[cdt][cdn]
	if (flt(item.initial_km) > 0 && flt(item.final_km) > 0 ){
		if ( flt(item.initial_km) > flt(item.final_km)){
			frappe.throw("Initial KM Cannot be greater than finial KM")
		}
		item.total_km = flt(item.final_km) - flt(item.initial_km)
		frm.refresh_field("items")
	}
}

var calculate_total_time = function(frm, cdt, cdn){
	let item = locals[cdt][cdn]
	if ( item.end_time &&  item.start_time){
		item.total_hours = frappe.datetime.get_hour_diff( item.end_time, item.start_time)
		frm.refresh_field("items")
	}
}