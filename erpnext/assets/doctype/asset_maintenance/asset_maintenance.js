// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Asset Maintenance', {
	setup: (frm) => {
		frm.set_query('assign_to', 'asset_maintenance_tasks', function(doc) {
			return {
				query: 'erpnext.assets.doctype.asset_maintenance.asset_maintenance.get_team_members',
				filters: {
					maintenance_team: doc.maintenance_team
				}
			};
		});

		frm.fields_dict.asset.get_query = function(doc) {
			return {
				filters: {
					'maintenance_required': 1
				}
			};
		};

		frm.fields_dict.serial_no.get_query = function(doc) {
			return {
				filters: {
					'asset': doc.asset
				}
			};
		};

		frm.set_indicator_formatter('maintenance_status',
			function(doc) {
				let indicator = 'blue';

				if (doc.maintenance_status == 'Overdue') {
					indicator = 'orange';
				}
				else if (doc.maintenance_status == 'Cancelled') {
					indicator = 'red';
				}

				return indicator;
			}
		);
	},

	refresh: (frm) => {
		frm.trigger('toggle_serial_no_and_num_of_assets');

		if (!frm.is_new()) {
			frm.trigger('make_dashboard');
		}
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

	make_dashboard: (frm) => {
		if (!frm.is_new()) {
			frappe.call({
				method: 'erpnext.assets.doctype.asset_maintenance.asset_maintenance.get_maintenance_log',
				args: {
					asset_name: frm.doc.asset
				},
				callback: (r) => {
					if(r.message) {
						const section = frm.dashboard.add_section('', __("Maintenance Log"));
						var rows = $('<div></div>').appendTo(section);

						(r.message || []).forEach(function(d) {
							$(`<div class='row' style='margin-bottom: 10px;'>
								<div class='col-sm-3 small'>
									<a onclick="frappe.set_route('List', 'Asset Maintenance Log_',
										{'asset_name': '${d.asset_name}','maintenance_status': '${d.maintenance_status}' });">
										${d.maintenance_status} <span class="badge">${d.count}</span>
									</a>
								</div>
							</div>`).appendTo(rows);
						});
						frm.dashboard.show();
					}
				}
			});
		}
	},

	num_of_assets: (frm) => {
		frappe.db.get_value('Asset', frm.doc.asset, ['is_serialized_asset', 'num_of_assets'], (r) => {
			if (r && !r.is_serialized_asset) {
				if (frm.doc.num_of_assets < r.num_of_assets) {
					frappe.msgprint({
						title: __('Warning'),
						message: __('Asset {0} will be split on saving this document as the Number of Assets entered \
							is less than {1}.', [frm.doc.asset, r.num_of_assets])
					});
				}
			}
		})
	}
});

frappe.ui.form.on('Asset Maintenance Task', {
	start_date: (frm, cdt, cdn)  => {
		get_next_due_date(frm, cdt, cdn);
	},
	periodicity: (frm, cdt, cdn)  => {
		get_next_due_date(frm, cdt, cdn);
	},
	last_completion_date: (frm, cdt, cdn)  => {
		get_next_due_date(frm, cdt, cdn);
	},
	end_date: (frm, cdt, cdn)  => {
		get_next_due_date(frm, cdt, cdn);
	}
});

var get_next_due_date = function (frm, cdt, cdn) {
	var d = locals[cdt][cdn];

	if (d.start_date && d.periodicity) {
		return frappe.call({
			method: 'erpnext.assets.doctype.asset_maintenance.asset_maintenance.calculate_next_due_date',
			args: {
				start_date: d.start_date,
				periodicity: d.periodicity,
				end_date: d.end_date,
				last_completion_date: d.last_completion_date,
				next_due_date: d.next_due_date
			},
			callback: function(r) {
				if (r.message) {
					frappe.model.set_value(cdt, cdn, 'next_due_date', r.message);
				}
				else {
					frappe.model.set_value(cdt, cdn, 'next_due_date', '');
				}
			}
		});
	}
};
