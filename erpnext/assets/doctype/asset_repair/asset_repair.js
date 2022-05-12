// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Asset Repair', {
	setup: function (frm) {
		frm.fields_dict.cost_center.get_query = function (doc) {
			return {
				filters: {
					'is_group': 0,
					'company': doc.company
				}
			};
		};

		frm.fields_dict.project.get_query = function (doc) {
			return {
				filters: {
					'company': doc.company
				}
			};
		};

		frm.fields_dict.warehouse.get_query = function (doc) {
			return {
				filters: {
					'is_group': 0,
					'company': doc.company
				}
			};
		};

		frm.fields_dict.serial_no.get_query = function (doc) {
			return {
				filters: {
					'asset': doc.asset
				}
			};
		};
	},

	refresh: function (frm) {
		frm.trigger('toggle_serial_no_and_num_of_assets');

		if (frm.doc.docstatus) {
			frm.add_custom_button(_('View General Ledger'), function () {
				frappe.route_options = {
					'voucher_no': frm.doc.name
				};
				frappe.set_route('query-report', 'General Ledger');
			});
		}
	},

	repair_status: (frm) => {
		if (frm.doc.completion_date && frm.doc.repair_status == 'Completed') {
			frappe.call({
				method: 'erpnext.assets.doctype.asset_repair.asset_repair.get_downtime',
				args: {
					'failure_date': frm.doc.failure_date,
					'completion_date': frm.doc.completion_date
				},
				callback: function (r) {
					if (r.message) {
						frm.set_value('downtime', r.message + ' Hrs');
					}
				}
			});
		}

		if (frm.doc.repair_status == 'Completed') {
			frm.set_value('completion_date', frappe.datetime.now_datetime());
		}
	},

	stock_items_on_form_rendered() {
		erpnext.setup_serial_or_batch_no();
	},

	asset: (frm) => {
		frm.trigger('toggle_serial_no_and_num_of_assets');
	},

	toggle_serial_no_and_num_of_assets: (frm) => {
		if (frm.doc.asset) {
			frappe.db.get_value('Asset', frm.doc.asset, ['is_serialized_asset', 'num_of_assets'], (r) => {
				if (r && r.is_serialized_asset) {
					frm.set_df_property('serial_no', 'hidden', 0);
					frm.set_df_property('serial_no', 'reqd', 1);

					frm.set_value('num_of_assets', 0);
					frm.set_df_property('num_of_assets', 'hidden', 1);
					frm.set_df_property('num_of_assets', 'reqd', 0);
				} else {
					frm.set_df_property('serial_no', 'hidden', 1);
					frm.set_df_property('serial_no', 'reqd', 0);
					frm.set_value('serial_no', '');

					if (r.num_of_assets > 1) {
						if (!frm.doc.num_of_assets) {
							frm.set_value('num_of_assets', r.num_of_assets);
						}

						frm.set_df_property('num_of_assets', 'hidden', 0);
						frm.set_df_property('num_of_assets', 'reqd', 1);
					} else {
						frm.set_df_property('num_of_assets', 'reqd', 0);
					}
				}
			});
		} else {
			frm.set_df_property('serial_no', 'hidden', 1);
			frm.set_df_property('num_of_assets', 'hidden', 1);
		}
	},

	num_of_assets: (frm) => {
		frappe.db.get_value('Asset', frm.doc.asset, ['is_serialized_asset', 'num_of_assets'], (r) => {
			if (r && !r.is_serialized_asset) {
				if (frm.doc.num_of_assets < r.num_of_assets) {
					frappe.msgprint({
						title: __('Warning'),
						message: __('Asset {0} will be split on submitting this repair as the Number of Assets entered \
							is less than {1}.', [frm.doc.asset, r.num_of_assets])
					});
				}
			}
		});
	}
});

frappe.ui.form.on('Asset Repair Consumed Item', {
	item_code: function (frm, cdt, cdn) {
		var item = locals[cdt][cdn];

		let item_args = {
			'item_code': item.item_code,
			'warehouse': frm.doc.warehouse,
			'qty': item.qty,
			'serial_no': item.serial_no,
			'company': frm.doc.company
		};

		frappe.call({
			method: 'erpnext.stock.utils.get_incoming_rate',
			args: {
				args: item_args
			},
			callback: function (r) {
				frappe.model.set_value(cdt, cdn, 'rate', r.message);
			}
		});
	},

	qty: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, 'amount', row.qty * row.rate);
	},
});
