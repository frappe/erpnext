// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.item");

frappe.ui.form.on("Item", {
	onload: function(frm) {
		erpnext.item.setup_queries(frm);
		if (frm.doc.variant_of){
			frm.fields_dict["attributes"].grid.set_column_disp("attribute_value", true);
		}

	},

	refresh: function(frm) {
		if(frm.doc.is_stock_item) {
			frm.add_custom_button(__("Show Balance"), function() {
				frappe.route_options = {
					"item_code": frm.doc.name
				}
				frappe.set_route("query-report", "Stock Balance");
			});
		}

		// make sensitive fields(has_serial_no, is_stock_item, valuation_method)
		// read only if any stock ledger entry exists
		erpnext.item.make_dashboard(frm);

		// clear intro
		frm.set_intro();

		if (frm.doc.has_variants) {
			frm.set_intro(__("This Item is a Template and cannot be used in transactions. Item attributes will be copied over into the variants unless 'No Copy' is set"), true);
			frm.add_custom_button(__("Show Variants"), function() {
				frappe.set_route("List", "Item", {"variant_of": frm.doc.name});
			}, "icon-list", "btn-default");

			frm.add_custom_button(__("Make Variant"), function() {
				erpnext.item.make_variant()
			}, "icon-list", "btn-default");
		}
		if (frm.doc.variant_of) {
			frm.set_intro(__("This Item is a Variant of {0} (Template). Attributes will be copied over from the template unless 'No Copy' is set", [frm.doc.variant_of]), true);
		}

		if (frappe.defaults.get_default("item_naming_by")!="Naming Series") {
			frm.toggle_display("naming_series", false);
		} else {
			erpnext.toggle_naming_series();
		}

		erpnext.item.edit_prices_button(frm);

		if (!frm.doc.__islocal && frm.doc.is_stock_item) {
			frm.toggle_enable(['has_serial_no', 'is_stock_item', 'valuation_method', 'has_batch_no'],
				(frm.doc.__onload && frm.doc.__onload.sle_exists=="exists") ? false : true);
		}

		erpnext.item.toggle_reqd(frm);

		erpnext.item.toggle_attributes(frm);
	},

	validate: function(frm){
		erpnext.item.weight_to_validate(frm);
	},

	image: function(frm) {
		refresh_field("image_view");
	},

	page_name: frappe.utils.warn_page_name_change,

	item_code: function(frm) {
		if(!frm.doc.item_name)
			frm.set_value("item_name", frm.doc.item_code);
		if(!frm.doc.description)
			frm.set_value("description", frm.doc.item_code);
	},

	copy_from_item_group: function(frm) {
		return frm.call({
			doc: frm.doc,
			method: "copy_specification_from_item_group"
		});
	},

	is_stock_item: function(frm) {
		erpnext.item.toggle_reqd(frm);
	},

	has_variants: function(frm) {
		erpnext.item.toggle_attributes(frm);
	}
});

$.extend(erpnext.item, {
	setup_queries: function(frm) {
		// Expense Account
		// ---------------------------------
		frm.fields_dict['expense_account'].get_query = function(doc) {
			return {
				filters: {
					"report_type": "Profit and Loss",
					"is_group": 0
				}
			}
		}

		// Income Account
		// --------------------------------
		frm.fields_dict['income_account'].get_query = function(doc) {
			return {
				query: "erpnext.controllers.queries.get_income_account"
			}
		}


		// Purchase Cost Center
		// -----------------------------
		frm.fields_dict['buying_cost_center'].get_query = function(doc) {
			return {
				filters:{ "is_group": 0 }
			}
		}


		// Sales Cost Center
		// -----------------------------
		frm.fields_dict['selling_cost_center'].get_query = function(doc) {
			return {
				filters:{ "is_group": 0 }
			}
		}


		frm.fields_dict['taxes'].grid.get_field("tax_type").get_query = function(doc, cdt, cdn) {
			return {
				filters: [
					['Account', 'account_type', 'in',
						'Tax, Chargeable, Income Account, Expense Account'],
					['Account', 'docstatus', '!=', 2]
				]
			}
		}

		frm.fields_dict['item_group'].get_query = function(doc,cdt,cdn) {
			return {
				filters: [
					['Item Group', 'docstatus', '!=', 2]
				]
			}
		}

		frm.fields_dict.customer_items.grid.get_field("customer_name").get_query = function(doc, cdt, cdn) {
			return { query: "erpnext.controllers.queries.customer_query" }
		}

		frm.fields_dict.supplier_items.grid.get_field("supplier").get_query = function(doc, cdt, cdn) {
			return { query: "erpnext.controllers.queries.supplier_query" }
		}

	},

	toggle_reqd: function(frm) {
		frm.toggle_reqd("default_warehouse", frm.doc.is_stock_item);
	},

	make_dashboard: function(frm) {
		frm.dashboard.reset();
		if(frm.doc.__islocal)
			return;
	},

	edit_prices_button: function(frm) {
		frm.add_custom_button(__("Add / Edit Prices"), function() {
			frappe.set_route("Report", "Item Price", {"item_code": frm.doc.name});
		}, "icon-money", "btn-default");
	},

	weight_to_validate: function(frm){
		if((frm.doc.nett_weight || frm.doc.gross_weight) && !frm.doc.weight_uom) {
			msgprint(__('Weight is mentioned,\nPlease mention "Weight UOM" too'));
			validated = 0;
		}
	},

	make_variant: function(doc) {
		var fields = []

		for(var i=0;i< cur_frm.doc.attributes.length;i++){
			var fieldtype, desc;
			var row = cur_frm.doc.attributes[i];
			if (row.numeric_values){
				fieldtype = "Float";
				desc = "Min Value: "+ row.from_range +" , Max Value: "+ row.to_range +", in Increments of: "+ row.increment
			}
			else {
				fieldtype = "Data";
				desc = ""
			}
			fields = fields.concat({
				"label": row.attribute,
				"fieldname": row.attribute,
				"fieldtype": fieldtype,
				"reqd": 1,
				"description": desc
			})
		}

		var d = new frappe.ui.Dialog({
			title: __("Make Variant"),
			fields: fields
		});

		d.set_primary_action(__("Make"), function() {
			args = d.get_values();
			if(!args) return;
			frappe.call({
				method:"erpnext.controllers.item_variant.get_variant",
				args: {
					"item": cur_frm.doc.name,
					"args": d.get_values()
				},
				callback: function(r) {
					// returns variant item
					if (r.message) {
						var variant = r.message;
						var msgprint_dialog = frappe.msgprint(__("Item Variant {0} already exists with same attributes",
							[repl('<a href="#Form/Item/%(item_encoded)s" class="strong variant-click">%(item)s</a>', {
								item_encoded: encodeURIComponent(variant),
								item: variant
							})]
						));
						msgprint_dialog.hide_on_page_refresh = true;
						msgprint_dialog.$wrapper.find(".variant-click").on("click", function() {
							d.hide();
						});
					} else {
						d.hide();
						frappe.call({
							method:"erpnext.controllers.item_variant.create_variant",
							args: {
								"item": cur_frm.doc.name,
								"args": d.get_values()
							},
							callback: function(r) {
								var doclist = frappe.model.sync(r.message);
								frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
							}
						});
					}
				}
			});
		});

		d.show();

		$.each(d.fields_dict, function(i, field) {

			if(field.df.fieldtype !== "Data") {
				return;
			}

			$(field.input_area).addClass("ui-front");

			field.$input.autocomplete({
				minLength: 0,
				minChars: 0,
				autoFocus: true,
				source: function(request, response) {
					frappe.call({
						method:"frappe.client.get_list",
						args:{
							doctype:"Item Attribute Value",
							filters: [
								["parent","=", i],
								["attribute_value", "like", request.term + "%"]
							],
							fields: ["attribute_value"]
						},
						callback: function(r) {
							if (r.message) {
								response($.map(r.message, function(d) { return d.attribute_value; }));
							}
						}
					});
				},
				select: function(event, ui) {
					field.$input.val(ui.item.value);
					field.$input.trigger("change");
				},
			}).on("focus", function(){
				setTimeout(function() {
					if(!field.$input.val()) {
						field.$input.autocomplete("search", "");
					}
				}, 500);
			});
		});
	},
	toggle_attributes: function(frm) {
		frm.toggle_display("attributes", frm.doc.has_variants || frm.doc.variant_of);
		frm.fields_dict.attributes.grid.toggle_reqd("attribute_value", frm.doc.variant_of ? 1 : 0);
		frm.fields_dict.attributes.grid.set_column_disp("attribute_value", frm.doc.variant_of ? 1 : 0);
	}
});

cur_frm.add_fetch('attribute', 'numeric_values', 'numeric_values');
cur_frm.add_fetch('attribute', 'from_range', 'from_range');
cur_frm.add_fetch('attribute', 'to_range', 'to_range');
cur_frm.add_fetch('attribute', 'increment', 'increment');
cur_frm.add_fetch('tax_type', 'tax_rate', 'tax_rate');
