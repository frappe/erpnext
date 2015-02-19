// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.item");

frappe.ui.form.on("Item", "refresh", function(frm) {
	if(frm.doc.is_stock_item) {
		frm.add_custom_button(__("Show Balance"), function() {
			frappe.route_options = {
				"item_code": frm.doc.name
			}
			frappe.set_route("query-report", "Stock Balance");
		});
	}
})

cur_frm.cscript.refresh = function(doc) {
	// make sensitive fields(has_serial_no, is_stock_item, valuation_method)
	// read only if any stock ledger entry exists

	cur_frm.cscript.make_dashboard();

	if (cur_frm.doc.has_variants) {
		cur_frm.set_intro(__("This Item is a Template and cannot be used in transactions. Item attributes will be copied over into the variants unless 'No Copy' is set"), true);
		cur_frm.add_custom_button(__("Show Variants"), function() {
			frappe.set_route("List", "Item", {"variant_of": cur_frm.doc.name});
		}, "icon-list", "btn-default");
	}
	if (cur_frm.doc.variant_of) {
		cur_frm.set_intro(__("This Item is a Variant of {0} (Template). Attributes will be copied over from the template unless 'No Copy' is set", [cur_frm.doc.variant_of]), true);
	}

	if (frappe.defaults.get_default("item_naming_by")!="Naming Series") {
		cur_frm.toggle_display("naming_series", false);
	} else {
		erpnext.toggle_naming_series();
	}


	cur_frm.cscript.edit_prices_button();

	if (!doc.__islocal && doc.is_stock_item == 'Yes') {
		cur_frm.toggle_enable(['has_serial_no', 'is_stock_item', 'valuation_method', 'has_batch_no'],
			(doc.__onload && doc.__onload.sle_exists=="exists") ? false : true);
	}

	erpnext.item.toggle_reqd(cur_frm);
}

erpnext.item.toggle_reqd = function(frm) {
	frm.toggle_reqd("default_warehouse", frm.doc.is_stock_item==="Yes");
};

frappe.ui.form.on("Item", "onload", function(frm) {
	var df = frappe.meta.get_docfield("Item Variant", "item_attribute_value");
	df.on_make = function(field) {
		field.$input.autocomplete({
			minLength: 0,
			minChars: 0,
			source: function(request, response) {
				frappe.call({
					method:"frappe.client.get_list",
					args:{
						doctype:"Item Attribute Value",
						filters: [
							["parent","=", field.doc.item_attribute],
							["attribute_value", "like", request.term + "%"]
						],
						fields: ["attribute_value"]
					},
					callback: function(r) {
						response($.map(r.message, function(d) { return d.attribute_value; }));
					}
				});
			},
			select: function(event, ui) {
				field.$input.val(ui.item.value);
				field.$input.trigger("change");
			},
			focus: function( event, ui ) {
				if(ui.item.action) {
					return false;
				}
			},
		});
	}
});

cur_frm.cscript.make_dashboard = function() {
	cur_frm.dashboard.reset();
	if(cur_frm.doc.__islocal)
		return;
}

cur_frm.cscript.edit_prices_button = function() {
	cur_frm.add_custom_button(__("Add / Edit Prices"), function() {
		frappe.set_route("Report", "Item Price", {"item_code": cur_frm.doc.name});
	}, "icon-money", "btn-default");
}

cur_frm.cscript.item_code = function(doc) {
	if(!doc.item_name)
		cur_frm.set_value("item_name", doc.item_code);
	if(!doc.description)
		cur_frm.set_value("description", doc.item_code);
}

// Expense Account
// ---------------------------------
cur_frm.fields_dict['expense_account'].get_query = function(doc) {
	return {
		filters: {
			"report_type": "Profit and Loss",
			"group_or_ledger": "Ledger"
		}
	}
}

// Income Account
// --------------------------------
cur_frm.fields_dict['income_account'].get_query = function(doc) {
	return {
		filters: {
			"report_type": "Profit and Loss",
			'group_or_ledger': "Ledger",
			'account_type': "Income Account"
		}
	}
}


// Purchase Cost Center
// -----------------------------
cur_frm.fields_dict['buying_cost_center'].get_query = function(doc) {
	return {
		filters:{ 'group_or_ledger': "Ledger" }
	}
}


// Sales Cost Center
// -----------------------------
cur_frm.fields_dict['selling_cost_center'].get_query = function(doc) {
	return {
		filters:{ 'group_or_ledger': "Ledger" }
	}
}


cur_frm.fields_dict['taxes'].grid.get_field("tax_type").get_query = function(doc, cdt, cdn) {
	return {
		filters: [
			['Account', 'account_type', 'in',
				'Tax, Chargeable, Income Account, Expense Account'],
			['Account', 'docstatus', '!=', 2]
		]
	}
}

cur_frm.cscript.tax_type = function(doc, cdt, cdn){
	var d = locals[cdt][cdn];
	return get_server_fields('get_tax_rate', d.tax_type, 'taxes', doc, cdt, cdn, 1);
}

cur_frm.fields_dict['item_group'].get_query = function(doc,cdt,cdn) {
	return {
		filters: [
			['Item Group', 'docstatus', '!=', 2]
		]
	}
}

// Quotation to validation - either customer or lead mandatory
cur_frm.cscript.weight_to_validate = function(doc, cdt, cdn){
	if((doc.nett_weight || doc.gross_weight) && !doc.weight_uom) {
		msgprint(__('Weight is mentioned,\nPlease mention "Weight UOM" too'));
		validated = 0;
	}
}

cur_frm.cscript.validate = function(doc, cdt, cdn){
	cur_frm.cscript.weight_to_validate(doc, cdt, cdn);
}

cur_frm.fields_dict.customer_items.grid.get_field("customer_name").get_query = function(doc, cdt, cdn) {
	return { query: "erpnext.controllers.queries.customer_query" }
}

cur_frm.fields_dict.supplier_items.grid.get_field("supplier").get_query = function(doc, cdt, cdn) {
	return { query: "erpnext.controllers.queries.supplier_query" }
}

cur_frm.cscript.copy_from_item_group = function(doc) {
	return cur_frm.call({
		doc: doc,
		method: "copy_specification_from_item_group"
	});
}

cur_frm.cscript.image = function() {
	refresh_field("image_view");
}
