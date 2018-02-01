// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.asset");

frappe.ui.form.on('Asset', {
	onload: function(frm) {
		frm.set_query("item_code", function() {
			return {
				"filters": {
					"disabled": 0,
					"is_fixed_asset": 1,
					"is_stock_item": 0
				}
			};
		});

		frm.set_query("warehouse", function() {
			return {
				"filters": {
					"company": frm.doc.company,
					"is_group": 0
				}
			};
		});
	},

	refresh: function(frm) {
		frappe.ui.form.trigger("Asset", "is_existing_asset");
		frm.toggle_display("next_depreciation_date", frm.doc.docstatus < 1);
		frm.events.make_schedules_editable(frm);

		if (frm.doc.docstatus==1) {
			if (in_list(["Submitted", "Partially Depreciated", "Fully Depreciated"], frm.doc.status)) {
				frm.add_custom_button("Transfer Asset", function() {
					erpnext.asset.transfer_asset(frm);
				});

				frm.add_custom_button("Scrap Asset", function() {
					erpnext.asset.scrap_asset(frm);
				});

				frm.add_custom_button("Sell Asset", function() {
					frm.trigger("make_sales_invoice");
				});

			} else if (frm.doc.status=='Scrapped') {
				frm.add_custom_button("Restore Asset", function() {
					erpnext.asset.restore_asset(frm);
				});
			}
			if (frm.doc.status=='Submitted' && !frm.doc.is_existing_asset && !frm.doc.purchase_invoice) {
				frm.add_custom_button(__("Purchase Invoice"), function() {
					frm.trigger("make_purchase_invoice");
				}, __("Make"));
			}
			if (frm.doc.maintenance_required && !frm.doc.maintenance_schedule) {
				frm.add_custom_button(__("Asset Maintenance"), function() {
					frm.trigger("create_asset_maintenance");
				}, __("Make"));
			}
			frm.page.set_inner_btn_group_as_primary(__("Make"));
			frm.trigger("setup_chart");
		}
	},

	setup_chart: function(frm) {
		var x_intervals = [frm.doc.purchase_date];
		var asset_values = [frm.doc.gross_purchase_amount];
		var last_depreciation_date = frm.doc.purchase_date;

		if(frm.doc.opening_accumulated_depreciation) {
			last_depreciation_date = frappe.datetime.add_months(frm.doc.next_depreciation_date,
				-1*frm.doc.frequency_of_depreciation);

			x_intervals.push(last_depreciation_date);
			asset_values.push(flt(frm.doc.gross_purchase_amount) -
				flt(frm.doc.opening_accumulated_depreciation));
		}

		$.each(frm.doc.schedules || [], function(i, v) {
			x_intervals.push(v.schedule_date);
			var asset_value = flt(frm.doc.gross_purchase_amount) - flt(v.accumulated_depreciation_amount);
			if(v.journal_entry) {
				last_depreciation_date = v.schedule_date;
				asset_values.push(asset_value);
			} else {
				if (in_list(["Scrapped", "Sold"], frm.doc.status)) {
					asset_values.push(null);
				} else {
					asset_values.push(asset_value)
				}
			}
		});

		if(in_list(["Scrapped", "Sold"], frm.doc.status)) {
			x_intervals.push(frm.doc.disposal_date);
			asset_values.push(0);
			last_depreciation_date = frm.doc.disposal_date;
		}

		frm.dashboard.render_graph({
			title: "Asset Value",
			data: {
				labels: x_intervals,
				datasets: [{
					color: 'green',
					values: asset_values,
					formatted: asset_values.map(d => d.toFixed(2))
				}]
			},
			type: 'line'
		});
	},


	item_code: function(frm) {
		if(frm.doc.item_code) {
			frappe.call({
				method: "erpnext.assets.doctype.asset.asset.get_item_details",
				args: {
					item_code: frm.doc.item_code
				},
				callback: function(r, rt) {
					if(r.message) {
						$.each(r.message, function(field, value) {
							frm.set_value(field, value);
						})
					}
				}
			})
		}
	},

	is_existing_asset: function(frm) {
		frm.toggle_reqd("next_depreciation_date", (!frm.doc.is_existing_asset && frm.doc.calculate_depreciation));
	},

	opening_accumulated_depreciation: function(frm) {
		erpnext.asset.set_accululated_depreciation(frm);
	},

	depreciation_method: function(frm) {
		frm.events.make_schedules_editable(frm);
	},

	make_schedules_editable: function(frm) {
		var is_editable = frm.doc.depreciation_method==="Manual" ? true : false;
		frm.toggle_enable("schedules", is_editable);
		frm.fields_dict["schedules"].grid.toggle_enable("schedule_date", is_editable);
		frm.fields_dict["schedules"].grid.toggle_enable("depreciation_amount", is_editable);
	},

	make_purchase_invoice: function(frm) {
		frappe.call({
			args: {
				"asset": frm.doc.name,
				"item_code": frm.doc.item_code,
				"gross_purchase_amount": frm.doc.gross_purchase_amount,
				"company": frm.doc.company,
				"posting_date": frm.doc.purchase_date
			},
			method: "erpnext.assets.doctype.asset.asset.make_purchase_invoice",
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		})
	},

	make_sales_invoice: function(frm) {
		frappe.call({
			args: {
				"asset": frm.doc.name,
				"item_code": frm.doc.item_code,
				"company": frm.doc.company
			},
			method: "erpnext.assets.doctype.asset.asset.make_sales_invoice",
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		})
	},

	create_asset_maintenance: function(frm) {
		frappe.call({
			args: {
				"asset": frm.doc.name,
				"item_code": frm.doc.item_code,
				"item_name": frm.doc.item_name,
				"asset_category": frm.doc.asset_category,
				"company": frm.doc.company
			},
			method: "erpnext.assets.doctype.asset.asset.create_asset_maintenance",
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		})
	}
});

frappe.ui.form.on('Depreciation Schedule', {
	make_depreciation_entry: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (!row.journal_entry) {
			frappe.call({
				method: "erpnext.assets.doctype.asset.depreciation.make_depreciation_entry",
				args: {
					"asset_name": frm.doc.name,
					"date": row.schedule_date
				},
				callback: function(r) {
					frappe.model.sync(r.message);
					frm.refresh();
				}
			})
		}
	},

	depreciation_amount: function(frm, cdt, cdn) {
		erpnext.asset.set_accululated_depreciation(frm);
	}

})

erpnext.asset.set_accululated_depreciation = function(frm) {
	if(frm.doc.depreciation_method != "Manual") return;

	var accumulated_depreciation = flt(frm.doc.opening_accumulated_depreciation);
	$.each(frm.doc.schedules || [], function(i, row) {
		accumulated_depreciation  += flt(row.depreciation_amount);
		frappe.model.set_value(row.doctype, row.name,
			"accumulated_depreciation_amount", accumulated_depreciation);
	})
};

erpnext.asset.scrap_asset = function(frm) {
	frappe.confirm(__("Do you really want to scrap this asset?"), function () {
		frappe.call({
			args: {
				"asset_name": frm.doc.name
			},
			method: "erpnext.assets.doctype.asset.depreciation.scrap_asset",
			callback: function(r) {
				cur_frm.reload_doc();
			}
		})
	})
};

erpnext.asset.restore_asset = function(frm) {
	frappe.confirm(__("Do you really want to restore this scrapped asset?"), function () {
		frappe.call({
			args: {
				"asset_name": frm.doc.name
			},
			method: "erpnext.assets.doctype.asset.depreciation.restore_asset",
			callback: function(r) {
				cur_frm.reload_doc();
			}
		})
	})
};

erpnext.asset.transfer_asset = function(frm) {
	var dialog = new frappe.ui.Dialog({
		title: __("Transfer Asset"),
		fields: [
			{
				"label": __("Target Warehouse"),
				"fieldname": "target_warehouse",
				"fieldtype": "Link",
				"options": "Warehouse",
				"get_query": function () {
					return {
						filters: [
							["Warehouse", "company", "in", ["", cstr(frm.doc.company)]],
							["Warehouse", "is_group", "=", 0]
						]
					}
				},
				"reqd": 1
			},
			{
				"label": __("Date"),
				"fieldname": "transfer_date",
				"fieldtype": "Datetime",
				"reqd": 1,
				"default": frappe.datetime.now_datetime()
			}
		]
	});

	dialog.set_primary_action(__("Transfer"), function() {
		var args = dialog.get_values();
		if(!args) return;
		dialog.hide();
		return frappe.call({
			type: "GET",
			method: "erpnext.assets.doctype.asset.asset.transfer_asset",
			args: {
				args: {
					"asset": frm.doc.name,
					"transaction_date": args.transfer_date,
					"source_warehouse": frm.doc.warehouse,
					"target_warehouse": args.target_warehouse,
					"company": frm.doc.company
				}
			},
			freeze: true,
			callback: function(r) {
				cur_frm.reload_doc();
			}
		})
	});
	dialog.show();
};