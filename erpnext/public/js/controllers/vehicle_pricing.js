frappe.provide("erpnext.vehicles.pricing");

$.extend(erpnext.vehicles.pricing, {
	pricing_component_query: function (component_type) {
		return {
			filters: {
				component_type: component_type
			}
		}
	},

	pricing_component_route_options: function (component_type) {
		return {
			component_type: component_type
		}
	},

	calculate_total_price: function (frm, table_field, total_field) {
		if (!total_field) {
			return;
		}

		frm.doc[total_field] = 0;
		$.each(frm.doc[table_field] || [], function (i, d) {
			frappe.model.round_floats_in(d);
			frm.doc[total_field] += flt(d.component_amount);
		});

		frm.doc[total_field] = flt(frm.doc[total_field], precision(total_field));
	},

	get_pricing_components: function (opts) {
		var args = opts.args;
		var frm = opts.frm;
		if (!args) {
			if (frm) {
				args = erpnext.vehicles.pricing.get_pricing_args(frm);
			} else {
				args = {};
			}
		}

		if (opts.component_type && args.company && args.item_code) {
			return frappe.call({
				method: "erpnext.vehicles.vehicle_pricing.get_pricing_components",
				args: {
					component_type: opts.component_type,
					args: args,
					get_selling_components: cint(opts.get_selling_components || opts.selling_components_field),
					get_buying_components: cint(opts.get_buying_components || opts.buying_components_field),
					filters: opts.filters
				},
				callback: function (r) {
					if (!r.exc) {
						if (frm) {
							if (opts.selling_components_field && r.message.selling) {
								erpnext.vehicles.pricing.apply_pricing_components(frm, opts.selling_components_field,
									r.message.selling, opts.clear_table, opts.update_amount);
							}
							if (opts.buying_components_field && r.message.buying) {
								erpnext.vehicles.pricing.apply_pricing_components(frm, opts.buying_components_field,
									r.message.buying, opts.clear_table, opts.update_amount);
							}
							if (r.message.doc) {
								frm.set_value(r.message.doc);
							}
						}
						if (opts.callback) {
							opts.callback(r);
						}
					}
				}
			});
		}
	},

	get_component_details: function (opts) {
		var args = opts.args;
		var frm = opts.frm;
		var row = opts.row;
		if (!args) {
			if (frm) {
				args = erpnext.vehicles.pricing.get_pricing_args(frm);
			} else {
				args = {};
			}
		}

		if (opts.component_name && opts.selling_or_buying && args.company && args.item_code) {
			return frappe.call({
				method: "erpnext.vehicles.vehicle_pricing.get_component_details",
				args: {
					component_name: opts.component_name,
					args: args,
					selling_or_buying: opts.selling_or_buying,
				},
				callback: function (r) {
					if (!r.exc) {
						if (frm) {
							if (row) {
								row = locals[row.doctype][row.name];
								$.each(r.message.component || {}, function (key, value) {
									row[key] = value;
								});
								frm.fields_dict[row.parentfield].refresh();
							}

							if (r.message.doc) {
								frm.set_value(r.message.doc);
							}
						}

						if (opts.callback) {
							opts.callback(r);
						}
					}
				}
			});
		}
	},

	apply_pricing_components: function (frm, table_field, components, clear_table, update_amount) {
		if (clear_table) {
			frm.clear_table(table_field);
		}

		$.each(components || [], function (i, component_details) {
			if (component_details.component) {
				var row = (frm.doc[table_field] || []).filter(d => d.component == component_details.component);
				if (row.length) {
					row = row[0];
					$.each(component_details || {}, function (key, value) {
						if (key == "component_amount") {
							if (update_amount && flt(value)) {
								row[key] = flt(value, precision(key, row));
							}
						} else {
							row[key] = value;
						}
					});
				} else {
					row = frm.add_child(table_field, component_details);
				}
			}
		});

		frm.fields_dict[table_field].refresh();
	},

	remove_components: function (frm, table_field, filters) {
		if (frm && table_field && filters) {
			var parent_field = frm.get_field(table_field);
			if (parent_field) {
				var rows = (frm.doc[table_field] || []).filter(d => filters(d));
				$.each(rows, function (i, row) {
					var grid_row = parent_field.grid.grid_rows_by_docname[row.name];
					if (grid_row) {
						grid_row.remove();
					}
				});
			}
		}
	},

	get_pricing_args: function (frm) {
		var tax_status = cstr(frm.doc.tax_status);
		if (!tax_status && frm.doc.doctype == "Vehicle Quotation") {
			tax_status = "Filer";
		}

		var args = {
			company: frm.doc.company,
			item_code: frm.doc.item_code,
			territory: frm.doc.territory,
			transaction_date: frm.doc.posting_date || frm.doc.transaction_date,
			tax_status: tax_status,
			do_not_apply_withholding_tax: cint(frm.doc.do_not_apply_withholding_tax),
			doctype: frm.doc.doctype,
			name: frm.doc.name,
		};

		if (frm.doc.doctype == "Vehicle Registration Order") {
			args['choice_number_required'] = cint(frm.doc.choice_number_required);
		}

		return args;
	},
});
