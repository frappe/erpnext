// Common UI functionality for applies_to fields

frappe.ui.form.on(cur_frm.doctype, {
	refresh: function(frm) {
		frm.trigger("set_applies_to_read_only");
	},

	onload: function(frm) {
		frm.set_query('vehicle_color', () => {
			return erpnext.queries.vehicle_color({item_code: frm.doc.applies_to_item});
		});
	},

	applies_to_vehicle: function (frm) {
		frm.trigger("set_applies_to_read_only");
		frm.trigger("get_applies_to_details");
	},

	applies_to_item: function(frm) {
		frm.trigger("get_applies_to_details");
	},

	set_applies_to_read_only: function(frm) {
		var read_only_fields = [
			'applies_to_item', 'applies_to_item_name',
			'vehicle_license_plate', 'vehicle_unregistered',
			'vehicle_chassis_no', 'vehicle_engine_no',
			'vehicle_color', 'vehicle_last_odometer',
			'vehicle_warranty_no', 'vehicle_delivery_date',
		];
		$.each(read_only_fields, function (i, f) {
			if (frm.fields_dict[f]) {
				frm.set_df_property(f, "read_only", frm.doc.applies_to_vehicle ? 1 : 0);
			}
		});
	},

	get_applies_to_details: function(frm) {
		var args =  {
			applies_to_item: frm.doc.applies_to_item,
			applies_to_vehicle: frm.doc.applies_to_vehicle,
			doctype: frm.doc.doctype,
			name: frm.doc.name,
		};
		return frappe.call({
			method: "erpnext.stock.get_item_details.get_applies_to_details",
			args: {
				args: args
			},
			callback: function(r) {
				if(!r.exc) {
					return frm.set_value(r.message);
				}
			}
		});
	},

	get_applies_to_vehicle_odometer: function (frm) {
		if (!frm.doc.applies_to_vehicle || !frm.fields_dict.vehicle_last_odometer) {
			return;
		}

		return frappe.call({
			method: "erpnext.stock.get_item_details.get_applies_to_vehicle_odometer",
			args: {
				vehicle: frm.doc.applies_to_vehicle,
				project: frm.doc.project,
			},
			callback: function(r) {
				if(!r.exc) {
					frm.set_value('vehicle_last_odometer', r.message);
				}
			}
		});
	},

})
