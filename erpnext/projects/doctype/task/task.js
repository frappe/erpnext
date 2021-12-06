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
		frm.set_query("project_warehouse", function(doc) {
			return {
				filters: {
					"company": doc.company
				}
			};
		});

		frm.set_query("warehouse", "items", function(doc) {
			return {
				filters: {
					"company": doc.company
				}
			};
		});

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
		let hide = false;
		if (frm.doc.items.length > 0) {
			frm.doc.items.forEach((item) => {
				if (item.transferred > 0 | item.issued > 0) {
					hide = true;
				}
			})
			frm.toggle_display(["get_items"], hide == true ? 0 : 1);
			frm.set_df_property("from_bom", "read_only", hide == true ? 1 : 0);
			frm.set_df_property("qty", "read_only", hide == true ? 1 : 0);
			frm.set_df_property("use_multi_level_bom", "read_only", hide == true ? 1 : 0);
		}

		if (frm.doc.items.length) {
			frappe.call({
				method: "erpnext.projects.doctype.task.task.check_items_complete",
				args: {
					items: frm.doc.items
				},
				callback: function (r) {
					if (!r.message) {
						frm.add_custom_button(__('Material Transfer'), function(){
							frm.events.make_se_mt(frm)
						}, __("Create"));
						frm.add_custom_button(__('Material Issue'), function(){
							frm.events.make_se_mi(frm)
						}, __("Create"));
					}
				}
			})
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
	calculate_estimated_cost: function(frm, row) {
		row.estimated_cost = flt(row.qty) * flt(row.basic_rate);
		frm.refresh_field("items")
	},
	get_items(frm) {
		if (!frm.doc.qty || !frm.doc.from_bom) {
			frappe.throw(__('BOM and Quantity is required to fetch items.'));
		}
		frm.doc.items = [];
	 	frappe.call({
			doc: frm.doc,
			method: 'get_items',
			callback: (r) => {
				frm.refresh_fields("items");
			}
		});
	}
});
let items_before_delete = [];
frappe.ui.form.on("Task Item", {
	items_remove: function(frm) {
		frappe.call({
			method: "erpnext.projects.doctype.task.task.check_if_deletable",
			args: {
				items: items_before_delete,
			},
			always: function (r) {
				if (r.exc) {
					frm.reload_doc();
					items_before_delete = [];
				}
			},
		})
	},
	warehouse(frm, cdt, cdn){
		const row = locals[cdt][cdn];
		frappe.call({
			doc: frm.doc,
			method: "get_basic_rate",
			args: {
				item: {"item_code": row.item_code, "stock_uom": row.uom, "source_warehouse": row.warehouse},
			},
			callback: function (r) {
				frappe.model.set_value(cdt, cdn, 'basic_rate', r.message);
				frm.events.calculate_estimated_cost(frm, row);
			},
		})
	},
	before_items_remove: function (frm) {
		items_before_delete = frm.doc.items
	},
	basic_rate(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		frm.events.calculate_estimated_cost(frm, row);
	}
});

