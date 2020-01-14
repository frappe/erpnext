// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Routing', {
	calculate_operating_cost: function(frm, child) {
		const operating_cost = flt(flt(child.hour_rate) * flt(child.time_in_mins) / 60, 2);
		frappe.model.set_value(child.doctype, child.name, "operating_cost", operating_cost);
	}
});

frappe.ui.form.on('BOM Operation', {
	operation: function(frm, cdt, cdn) {
		const d = locals[cdt][cdn];

		if(!d.operation) return;

		frappe.call({
			"method": "frappe.client.get",
			args: {
				doctype: "Operation",
				name: d.operation
			},
			callback: function (data) {
				if (data.message.description) {
					frappe.model.set_value(d.doctype, d.name, "description", data.message.description);
				}

				if (data.message.workstation) {
					frappe.model.set_value(d.doctype, d.name, "workstation", data.message.workstation);
				}

				frm.events.calculate_operating_cost(frm, d);
			}
		});
	},

	workstation: function(frm, cdt, cdn) {
		const d = locals[cdt][cdn];

		frappe.call({
			"method": "frappe.client.get",
			args: {
				doctype: "Workstation",
				name: d.workstation
			},
			callback: function (data) {
				frappe.model.set_value(d.doctype, d.name, "base_hour_rate", data.message.hour_rate);
				frappe.model.set_value(d.doctype, d.name, "hour_rate", data.message.hour_rate);
				frm.events.calculate_operating_cost(frm, d);
			}
		});
	},

	time_in_mins: function(frm, cdt, cdn) {
		const d = locals[cdt][cdn];
		frm.events.calculate_operating_cost(frm, d);
	}
});