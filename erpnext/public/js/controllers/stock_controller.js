// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.stock");

erpnext.stock.StockController = class StockController extends frappe.ui.form.Controller {
	onload() {
		// warehouse query if company
		if (this.frm.fields_dict.company) {
			this.setup_warehouse_query();
		}
	}

	setup_warehouse_query() {
		var me = this;
		erpnext.queries.setup_queries(this.frm, "Warehouse", function(fieldname) {
			return erpnext.queries.warehouse(me.frm.doc,
				me.get_warehouse_filters && me.get_warehouse_filters.bind(me, fieldname));
		});
	}

	setup_posting_date_time_check() {
		// make posting date default and read only unless explictly checked
		frappe.ui.form.on(this.frm.doctype, 'set_posting_date_and_time_read_only', function(frm) {
			if(frm.doc.docstatus == 0 && frm.doc.set_posting_time) {
				frm.set_df_property('posting_date', 'read_only', 0);
				frm.set_df_property('posting_time', 'read_only', 0);
			} else {
				frm.set_df_property('posting_date', 'read_only', 1);
				frm.set_df_property('posting_time', 'read_only', 1);
			}
		})

		frappe.ui.form.on(this.frm.doctype, 'set_posting_time', function(frm) {
			frm.trigger('set_posting_date_and_time_read_only');
		});

		frappe.ui.form.on(this.frm.doctype, 'refresh', function(frm) {
			// set default posting date / time
			if(frm.doc.docstatus==0) {
				if(!frm.doc.posting_date) {
					frm.set_value('posting_date', frappe.datetime.nowdate());
				}
				if(!frm.doc.posting_time) {
					frm.set_value('posting_time', frappe.datetime.now_time());
				}
				frm.trigger('set_posting_date_and_time_read_only');
			}
		});
	}

	show_stock_ledger() {
		var me = this;
		if(this.frm.doc.docstatus===1) {
			cur_frm.add_custom_button(__("Stock Ledger"), function() {
				frappe.route_options = {
					voucher_no: me.frm.doc.name,
					from_date: me.frm.doc.posting_date,
					to_date: me.frm.doc.posting_date,
					company: me.frm.doc.company,
					group_by: "Ungrouped"
				};
				frappe.set_route("query-report", "Stock Ledger");
			}, __("View"));
		}
	}

	show_general_ledger() {
		var me = this;
		if(this.frm.doc.docstatus===1) {
			cur_frm.add_custom_button(__('Accounting Ledger'), function() {
				frappe.route_options = {
					voucher_no: me.frm.doc.name,
					from_date: me.frm.doc.posting_date,
					to_date: me.frm.doc.posting_date,
					company: me.frm.doc.company,
					merge_similar_entries: 0
				};
				frappe.set_route("query-report", "General Ledger");
			}, __("View"));
		}
	}

	get_applicable_items(items_type) {
		var me = this;

		var item_groups = [{
			"item_group": null
		}];

		var dialog = new frappe.ui.Dialog({
			title: __("Get Applicable Items"),
			fields: [
				{
					"fieldtype": "Link",
					"label": __("Applies To Item Code"),
					"fieldname": "applies_to_item",
					"options":"Item",
					"reqd": 1,
					"default": me.frm.doc.applies_to_item,
					onchange: () => {
						let item_code = dialog.get_value('applies_to_item');
						if (item_code) {
							frappe.db.get_value("Item", item_code, 'item_name', (r) => {
								if (r) {
									dialog.set_value('applies_to_item_name', r.item_name);
								}
							});
						} else {
							dialog.set_value('applies_to_item_name', "");
						}
					},
					get_query: () => erpnext.queries.item({'has_applicable_items': 1, 'include_templates': 1})
				},
				{
					"fieldtype": "Data",
					"label": __("Applies To Item Name"),
					"fieldname": "applies_to_item_name",
					"read_only": 1,
					"default": me.frm.doc.applies_to_item ? me.frm.doc.applies_to_item_name : "",
				},
				{
					"fieldtype": "Section Break",
				},
				{
					"fieldtype": "Table",
					"label": __("Item Groups"),
					"fieldname": "item_groups",
					"reqd": 1,
					"data": item_groups,
					"get_data": () => item_groups,
					"fields": [
						{
							"fieldtype": "Link",
							"label": __("Item Group"),
							"fieldname": "item_group",
							"options": "Item Group",
							"reqd": 1,
							"in_list_view": 1,
							get_query: () => {
								return { query: "erpnext.controllers.queries.applicable_item_group" }
							}
						},
					]
				},
			]
		});

		dialog.set_primary_action(__("Get Items"), function () {
			var args = dialog.get_values();
			if (!args.applies_to_item){
				return;
			}

			frappe.call({
				method: "erpnext.stock.doctype.item_applicable_item.item_applicable_item.add_applicable_items",
				args: {
					applies_to_item: args.applies_to_item,
					item_groups: args.item_groups.map(d => d.item_group).filter(d => d),
					target_doc: me.frm.doc,
					items_type: items_type,
				},
				callback: function (r) {
					if (!r.exc) {
						dialog.hide();
						frappe.model.sync(r.message);
						me.frm.dirty();
						me.frm.refresh_fields();
					}
				}
			});
		});

		dialog.show();
	}

	get_project_template_items(items_type) {
		var me = this;
		var dialog = new frappe.ui.Dialog({
			title: __("Get Project Template Items"),
			fields: [
				{
					"fieldtype": "Link",
					"label": __("Project Template"),
					"fieldname": "project_template",
					"options": "Project Template",
					"reqd": 1,
					onchange: () => {
						let project_template = dialog.get_value('project_template');
						if (project_template) {
							frappe.db.get_value("Project Template", project_template, 'project_template_name', (r) => {
								if (r) {
									dialog.set_value('project_template_name', r.project_template_name);
								}
							});
						}
					},
					get_query: () => erpnext.queries.project_template(dialog.get_value('applies_to_item')),
				},
				{
					"fieldtype": "Data",
					"label": __("Project Template Name"),
					"fieldname": "project_template_name",
					"read_only": 1,
				},
				{
					"fieldtype": "Link",
					"label": __("Applies To Item Code"),
					"fieldname": "applies_to_item",
					"options":"Item",
					"default": me.frm.doc.applies_to_item,
					onchange: () => {
						let item_code = dialog.get_value('applies_to_item');
						if (item_code) {
							frappe.db.get_value("Item", item_code, 'item_name', (r) => {
								if (r) {
									dialog.set_value('applies_to_item_name', r.item_name);
								}
							});
						} else {
							dialog.set_value('applies_to_item_name', "");
						}
					},
				},
				{
					"fieldtype": "Data",
					"label": __("Applies To Item Name"),
					"fieldname": "applies_to_item_name",
					"read_only": 1,
					"default": me.frm.doc.applies_to_item ? me.frm.doc.applies_to_item_name : "",
				},
				{
					"fieldtype": "Link",
					"label": __("Item Group"),
					"fieldname": "item_group",
					"options": "Item Group",
				},
			]
		});

		dialog.set_primary_action(__("Get Items"), function () {
			var args = dialog.get_values();
			if (!args.project_template){
				return;
			}

			frappe.call({
				method: "erpnext.projects.doctype.project_template.project_template.add_project_template_items",
				args: {
					project_template: args.project_template,
					applies_to_item: args.applies_to_item,
					item_group: args.item_group,
					target_doc: me.frm.doc,
					items_type: items_type,
				},
				callback: function (r) {
					if (!r.exc) {
						dialog.hide();
						frappe.model.sync(r.message);
						me.frm.dirty();
						me.frm.refresh_fields();
					}
				}
			});
		});

		dialog.show();
	}

	add_get_applicable_items_button(items_type) {
		var me = this;
		me.frm.add_custom_button(__("Applicable Items"), function() {
			me.get_applicable_items(items_type);
		}, __("Get Items From"));
	}

	add_get_project_template_items_button(items_type) {
		var me = this;
		me.frm.add_custom_button(__("Project Template"), function() {
			me.get_project_template_items(items_type);
		}, __("Get Items From"));
	}
};
