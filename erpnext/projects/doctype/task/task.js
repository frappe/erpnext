// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.projects");

frappe.ui.form.on("Task", {
	setup: function (frm) {
		frm.make_methods = {
			'Timesheet': () => frappe.model.open_mapped_doc({
				method: 'erpnext.projects.doctype.task.task.make_timesheet',
				frm: frm
			})
		}
	},

	onload: function (frm) {
		frm.set_query("task", "depends_on", function () {
			let filters = {
				name: ["!=", frm.doc.name]
			};
			if (frm.doc.project) filters["project"] = frm.doc.project;
			return {
				filters: filters
			};
		})

		frm.set_query("parent_task", function () {
			let filters = {
				"is_group": 1,
				"name": ["!=", frm.doc.name]
			};
			if (frm.doc.project) filters["project"] = frm.doc.project;
			return {
				filters: filters
			}
		});
	},
	refresh(frm) {
		if (frm.doc.items.length) {
			frm.add_custom_button(__('Material Transfer'), function(){
				frm.events.make_se_mt(frm)
			}, __("Create"));
			frm.add_custom_button(__('Material Issue'), function(){
				frm.events.make_se_mi(frm)
			}, __("Create"));
		}
	},

	is_group: function (frm) {
		frappe.call({
			method: "erpnext.projects.doctype.task.task.check_if_child_exists",
			args: {
				name: frm.doc.name
			},
			callback: function (r) {
				if (r.message.length > 0) {
					let message = __('Cannot convert Task to non-group because the following child Tasks exist: {0}.',
						[r.message.join(", ")]
					);
					frappe.msgprint(message);
					frm.reload_doc();
				}
			}
		})
	},

	validate: function (frm) {
		frm.doc.project && frappe.model.remove_from_locals("Project",
			frm.doc.project);
	},
	make_se_mt: function(frm) {
		frappe.model.open_mapped_doc({
			method: 'erpnext.projects.doctype.task.task.make_stock_entry_mt',
			frm: frm,
		});
	},
	make_se_mi: function(frm) {
		frappe.model.open_mapped_doc({
			method: 'erpnext.projects.doctype.task.task.make_stock_entry_mi',
			frm: frm,
		});
	},
	get_items(frm) {
		if (!frm.doc.qty || !frm.doc.from_bom) {
			frappe.throw(__('BOM and Quantity is required to fetch items.'));
		}
	 	frappe.call({
			doc: frm.doc,
			method: 'get_items',
			callback: (response) => {
				const items = response.message;
				for (const [key, item] of Object.entries(items)) {
					let row = frm.add_child("items");
					row.item_code = item.item_code;
					row.item_name = item.item_name;
					row.basic_rate = item.rate;
					row.qty = item.qty;
					row.uom = item.stock_uom;
					row.estimated_cost = flt(row.qty) * flt(row.basic_rate);
					row.warehouse = item.source_warehouse;
				  }
			frm.refresh_fields("items");
			}
		});
	}
});

frappe.ui.form.on("Task Item", {
	basic_rate(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		row.estimated_cost = flt(row.qty) * flt(row.basic_rate);
		frm.refresh()
	}
});
