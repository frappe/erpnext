// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Item Lead Time", {
	refresh(frm) {
		frm.trigger("setup_queries");
	},

	setup_queries(frm) {
		frm.set_query("bom_no", () => {
			return {
				filters: {
					item: frm.doc.item_code,
					docstatus: 1,
					with_operations: 1,
				},
			};
		});
	},

	shift_time_in_hours(frm) {
		frm.trigger("calculate_total_workstation_time");
	},

	no_of_workstations(frm) {
		frm.trigger("calculate_total_workstation_time");
	},

	no_of_shift(frm) {
		frm.trigger("calculate_total_workstation_time");
	},

	calculate_total_workstation_time(frm) {
		let total_workstation_time =
			frm.doc.shift_time_in_hours * frm.doc.no_of_workstations * frm.doc.no_of_shift;
		frm.set_value("total_workstation_time", total_workstation_time);
	},

	total_workstation_time(frm) {
		frm.trigger("calculate_no_of_units_produced");
	},

	manufacturing_time_in_mins(frm) {
		frm.trigger("calculate_no_of_units_produced");
	},

	calculate_no_of_units_produced(frm) {
		let no_of_units_produced =
			Math.ceil(frm.doc.total_workstation_time / frm.doc.manufacturing_time_in_mins) * 60;
		frm.set_value("no_of_units_produced", no_of_units_produced);
	},

	no_of_units_produced(frm) {
		frm.trigger("calculate_capacity_per_day");
	},

	daily_yield(frm) {
		frm.trigger("calculate_capacity_per_day");
	},

	calculate_capacity_per_day(frm) {
		let capacity_per_day = (frm.doc.daily_yield * frm.doc.no_of_units_produced) / 100;
		frm.set_value("capacity_per_day", Math.ceil(capacity_per_day));
	},
});
