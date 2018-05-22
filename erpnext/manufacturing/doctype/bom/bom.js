// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.bom");

frappe.ui.form.on("BOM", {
	setup: function(frm) {
		frm.add_fetch("item", "description", "description");
		frm.add_fetch("item", "image", "image");
		frm.add_fetch("item", "item_name", "item_name");
		frm.add_fetch("item", "stock_uom", "uom");

		frm.set_query("bom_no", "items", function() {
			return {
				filters: {
					'currency': frm.doc.currency,
					'company': frm.doc.company
				}
			};
		});

		frm.set_query("source_warehouse", "items", function() {
			return {
				filters: {
					'company': frm.doc.company
				}
			};
		});

		frm.set_query("item", function() {
			return {
				query: "erpnext.controllers.queries.item_query"
			};
		});

		frm.set_query("project", function() {
			return{
				filters:[
					['Project', 'status', 'not in', 'Completed, Cancelled']
				]
			};
		});

		frm.set_query("item_code", "items", function() {
			return {
				query: "erpnext.controllers.queries.item_query",
				filters: [["Item", "name", "!=", cur_frm.doc.item]]
			};
		});

		frm.set_query("bom_no", "items", function(doc, cdt, cdn) {
			var d = locals[cdt][cdn];
			return {
				filters: {
					'item': d.item_code,
					'is_active': 1,
					'docstatus': 1
				}
			};
		});

		// Child table indicator - Duplicate in refresh as well
		if (frm.doc.allow_alternative_item) {
			frm.set_indicator_formatter('item_code',
				function(doc) {
					return doc.set_alternative_items ? "orange" : ""
				}
			)
		}

	},

	onload_post_render: function(frm) {
		frm.get_field("items").grid.set_multiple_add("item_code", "qty");
	},
	refresh: function(frm) {
		frm.toggle_enable("item", frm.doc.__islocal);
		toggle_operations(frm);

		// Child table indicator
		if (frm.doc.allow_alternative_item) {
			frm.set_indicator_formatter('item_code',
				function(doc) {
					return doc.set_alternative_items ? "orange" : ""
				}
			)
		}

		if (!frm.doc.__islocal && frm.doc.docstatus<2) {
			frm.add_custom_button(__("Update Cost"), function() {
				frm.events.update_cost(frm);
			});
			frm.add_custom_button(__("Browse BOM"), function() {
				frappe.route_options = {
					"bom": frm.doc.name
				};
				frappe.set_route("Tree", "BOM");
			});
		}

		if(frm.doc.docstatus!=0) {
			frm.add_custom_button(__("Duplicate"), function() {
				frm.copy_doc();
			});
		}

	},

	update_cost: function(frm) {
		return frappe.call({
			doc: frm.doc,
			method: "update_cost",
			freeze: true,
			args: {
				update_parent: true,
				from_child_bom:false
			},
			callback: function(r) {
				if(!r.exc) frm.refresh_fields();
			}
		});
	}
});

erpnext.bom.BomController = erpnext.TransactionController.extend({
	conversion_rate: function(doc) {
		if(this.frm.doc.currency === this.get_company_currency()) {
			this.frm.set_value("conversion_rate", 1.0);
		} else {
			erpnext.bom.update_cost(doc);
		}
	},
	item_code: function(doc, cdt, cdn){
		var scrap_items = false;
		var child = locals[cdt][cdn];
		if(child.doctype == 'BOM Scrap Item') {
			scrap_items = true;
		}

		if (child.bom_no) {
			child.bom_no = '';
		}

		get_bom_material_detail(doc, cdt, cdn, scrap_items);
	},
	conversion_factor: function(doc, cdt, cdn) {
		if(frappe.meta.get_docfield(cdt, "stock_qty", cdn)) {
			var item = frappe.get_doc(cdt, cdn);
			frappe.model.round_floats_in(item, ["qty", "conversion_factor"]);
			item.stock_qty = flt(item.qty * item.conversion_factor, precision("stock_qty", item));
			refresh_field("stock_qty", item.name, item.parentfield);
			this.toggle_conversion_factor(item);
			this.frm.events.update_cost(this.frm);
		}
	},
});

$.extend(cur_frm.cscript, new erpnext.bom.BomController({frm: cur_frm}));

cur_frm.cscript.hour_rate = function(doc) {
	erpnext.bom.calculate_op_cost(doc);
	erpnext.bom.calculate_total(doc);
};

cur_frm.cscript.time_in_mins = cur_frm.cscript.hour_rate;

cur_frm.cscript.bom_no	= function(doc, cdt, cdn) {
	get_bom_material_detail(doc, cdt, cdn, false);
};

cur_frm.cscript.is_default = function(doc) {
	if (doc.is_default) cur_frm.set_value("is_active", 1);
};

var get_bom_material_detail= function(doc, cdt, cdn, scrap_items) {
	var d = locals[cdt][cdn];
	if (d.item_code) {
		return frappe.call({
			doc: doc,
			method: "get_bom_material_detail",
			args: {
				'item_code': d.item_code,
				'bom_no': d.bom_no != null ? d.bom_no: '',
				"scrap_items": scrap_items,
				'qty': d.qty
			},
			callback: function(r) {
				d = locals[cdt][cdn];
				$.extend(d, r.message);
				refresh_field("items");
				refresh_field("scrap_items");

				doc = locals[doc.doctype][doc.name];
				erpnext.bom.calculate_rm_cost(doc);
				erpnext.bom.calculate_scrap_materials_cost(doc);
				erpnext.bom.calculate_total(doc);
			},
			freeze: true
		});
	}
};

cur_frm.cscript.qty = function(doc) {
	erpnext.bom.calculate_rm_cost(doc);
	erpnext.bom.calculate_scrap_materials_cost(doc);
	erpnext.bom.calculate_total(doc);
};

cur_frm.cscript.rate = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	var scrap_items = false;

	if(cdt == 'BOM Scrap Item') {
		scrap_items = true;
	}

	if (d.bom_no) {
		frappe.msgprint(__("You can not change rate if BOM mentioned agianst any item"));
		get_bom_material_detail(doc, cdt, cdn, scrap_items);
	} else {
		erpnext.bom.calculate_rm_cost(doc);
		erpnext.bom.calculate_scrap_materials_cost(doc);
		erpnext.bom.calculate_total(doc);
	}
};

erpnext.bom.update_cost = function(doc) {
	erpnext.bom.calculate_op_cost(doc);
	erpnext.bom.calculate_rm_cost(doc);
	erpnext.bom.calculate_scrap_materials_cost(doc);
	erpnext.bom.calculate_total(doc);
};

erpnext.bom.calculate_op_cost = function(doc) {
	var op = doc.operations || [];
	doc.operating_cost = 0.0;
	doc.base_operating_cost = 0.0;

	for(var i=0;i<op.length;i++) {
		var operating_cost = flt(flt(op[i].hour_rate) * flt(op[i].time_in_mins) / 60, 2);
		var base_operating_cost = flt(operating_cost * doc.conversion_rate, 2);
		frappe.model.set_value('BOM Operation',op[i].name, "operating_cost", operating_cost);
		frappe.model.set_value('BOM Operation',op[i].name, "base_operating_cost", base_operating_cost);

		doc.operating_cost += operating_cost;
		doc.base_operating_cost += base_operating_cost;
	}
	refresh_field(['operating_cost', 'base_operating_cost']);
};

// rm : raw material
erpnext.bom.calculate_rm_cost = function(doc) {
	var rm = doc.items || [];
	var total_rm_cost = 0;
	var base_total_rm_cost = 0;
	for(var i=0;i<rm.length;i++) {
		var amount = flt(rm[i].rate) * flt(rm[i].qty);
		var base_amount = amount * flt(doc.conversion_rate);

		frappe.model.set_value('BOM Item', rm[i].name, 'base_rate',
			flt(rm[i].rate) * flt(doc.conversion_rate));
		frappe.model.set_value('BOM Item', rm[i].name, 'amount', amount);
		frappe.model.set_value('BOM Item', rm[i].name, 'base_amount', base_amount);
		frappe.model.set_value('BOM Item', rm[i].name,
			'qty_consumed_per_unit', flt(rm[i].stock_qty)/flt(doc.quantity));

		total_rm_cost += amount;
		base_total_rm_cost += base_amount;
	}
	cur_frm.set_value("raw_material_cost", total_rm_cost);
	cur_frm.set_value("base_raw_material_cost", base_total_rm_cost);
};

// sm : scrap material
erpnext.bom.calculate_scrap_materials_cost = function(doc) {
	var sm = doc.scrap_items || [];
	var total_sm_cost = 0;
	var base_total_sm_cost = 0;

	for(var i=0;i<sm.length;i++) {
		var base_rate = flt(sm[i].rate) * flt(doc.conversion_rate);
		var amount = flt(sm[i].rate) * flt(sm[i].stock_qty);
		var base_amount = amount * flt(doc.conversion_rate);

		frappe.model.set_value('BOM Scrap Item',sm[i].name, 'base_rate', base_rate);
		frappe.model.set_value('BOM Scrap Item',sm[i].name, 'amount', amount);
		frappe.model.set_value('BOM Scrap Item',sm[i].name, 'base_amount', base_amount);

		total_sm_cost += amount;
		base_total_sm_cost += base_amount;
	}

	cur_frm.set_value("scrap_material_cost", total_sm_cost);
	cur_frm.set_value("base_scrap_material_cost", base_total_sm_cost);
};

// Calculate Total Cost
erpnext.bom.calculate_total = function(doc) {
	var total_cost = flt(doc.operating_cost) + flt(doc.raw_material_cost) - flt(doc.scrap_material_cost);
	var base_total_cost = flt(doc.base_operating_cost) + flt(doc.base_raw_material_cost)
		- flt(doc.base_scrap_material_cost);

	cur_frm.set_value("total_cost", total_cost);
	cur_frm.set_value("base_total_cost", base_total_cost);
};

cur_frm.cscript.validate = function(doc) {
	erpnext.bom.update_cost(doc);
};

frappe.ui.form.on("BOM Operation", "operation", function(frm, cdt, cdn) {
	var d = locals[cdt][cdn];

	if(!d.operation) return;

	frappe.call({
		"method": "frappe.client.get",
		args: {
			doctype: "Operation",
			name: d.operation
		},
		callback: function (data) {
			if(data.message.description) {
				frappe.model.set_value(d.doctype, d.name, "description", data.message.description);
			}
			if(data.message.workstation) {
				frappe.model.set_value(d.doctype, d.name, "workstation", data.message.workstation);
			}
		}
	});
});

frappe.ui.form.on("BOM Operation", "workstation", function(frm, cdt, cdn) {
	var d = locals[cdt][cdn];

	frappe.call({
		"method": "frappe.client.get",
		args: {
			doctype: "Workstation",
			name: d.workstation
		},
		callback: function (data) {
			frappe.model.set_value(d.doctype, d.name, "base_hour_rate", data.message.hour_rate);
			frappe.model.set_value(d.doctype, d.name, "hour_rate",
				flt(flt(data.message.hour_rate) / flt(frm.doc.conversion_rate)), 2);

			erpnext.bom.calculate_op_cost(frm.doc);
			erpnext.bom.calculate_total(frm.doc);
		}
	});
});

frappe.ui.form.on("BOM Item", "qty", function(frm, cdt, cdn) {
	var d = locals[cdt][cdn];
	d.stock_qty = d.qty * d.conversion_factor;
	refresh_field("stock_qty", d.name, d.parentfield);
});

frappe.ui.form.on("BOM Item", "item_code", function(frm, cdt, cdn) {
	var d = locals[cdt][cdn];
	frappe.db.get_value('Item', {name: d.item_code}, 'allow_alternative_item', (r) => {
		d.allow_alternative_item = r.allow_alternative_item
	})
	frappe.db.get_value('Item', {name: d.item_code}, 'item_group', (r) => {
		d.item_group = r.item_group
	});

	refresh_field("allow_alternative_item", d.name, d.parentfield);
	refresh_field("item_qroup", d.name, d.parentfield);

});

frappe.ui.form.on("BOM Operation", "operations_remove", function(frm) {
	erpnext.bom.calculate_op_cost(frm.doc);
	erpnext.bom.calculate_total(frm.doc);
});

frappe.ui.form.on("BOM Item", "items_remove", function(frm) {
	erpnext.bom.calculate_rm_cost(frm.doc);
	erpnext.bom.calculate_total(frm.doc);
});

frappe.ui.form.on("BOM Item", "before_items_remove", function(frm, cdt, cdn) {
	// Remove related Child of child records
	var d = locals[cdt][cdn];
	if (d.item_code) {
		frappe.call({
			method: 'erpnext.manufacturing.doctype.bom.bom.remove_bomline_alt_items',
			args: {
				bom: frm.doc.name,
				parent_item_code: d.item_code
			},
			callback:function(r){
			}
		})
	}
});

frappe.ui.form.on("BOM Item", "item_code", function(frm, cdt, cdn) {
	// Set if Item has Allow Alternative in Item Master
	var d = locals[cdt][cdn];
	frappe.db.get_value('Item', {name: d.item_code}, 'allow_alternative_item', (r) => {
		d.has_alternatives = r.allow_alternative_item
	})
	refresh_field("has_alternatives", d.name, d.parentfield);
});

frappe.ui.form.on("BOM Item", "setup_alt_item_btn", function(frm, cdt, cdn) {
	var d = locals[cdt][cdn]
	if (cur_frm.doc.__islocal){
		// You must have at least reference to BOM parent
		// for setting up a alter
		frappe.throw("You must save before selecting Alternative Item")
    } else {
		cur_frm.select_bomline_alternate_items({
			frm: frm,
			cdn: cdn,
			cdt: cdt,
			item_code: d.item_code,
			has_alternatives: d.has_alternatives,
			bom: d.parent
		})
	}
});


cur_frm.select_bomline_alternate_items = function(opts) {
	const parent_item_code = opts.item_code;
	const bom = opts.bom;
	const cdn = opts.cdn;
	const cdt = opts.cdt;
	const has_alternatives = opts.has_alternatives;

	// headers for html rendering
	var headers = [ __("Alternative Item"), __("") ]
	// Global in the scope. Holds the child of child.
	cur_frm.alt_list_data = [];
	cur_frm.render_alts_items = function(d, headers, data){
		// render table of BOM Alternative Items
		d.fields_dict.alt_items.$wrapper.html(
			frappe.render_template('alternative_items_selector',
				{'header_columns': headers, 'data': cur_frm.alt_list_data}
			)
		)
	}
	cur_frm.set_alt_items = function(){
		var selected_items = []
		cur_frm.alt_list_data.forEach(function(item) {
		  selected_items.push(
			  '<a targer="_blank" href="#Form/Item/' + item.alt_item +'">' + item.alt_item + '</a> '
		  )
		});
		frappe.model.set_value('BOM Item', cdn, 'selected_alt_items', selected_items.join());
	}
	const d = new frappe.ui.Dialog({
		title: __("Select Alternate Items:") + parent_item_code,
		fields: [
			{
				fieldtype:'Link',
				fieldname:"add_alt_item",
				options: 'Item',
				depends_on: 'eval:'+ has_alternatives,
				label: __('Add pre-defined Alternative Item'),
				onchange: function() {
					var item_code = this.get_value();
  				  	if (item_code) {
						d.set_value("add_alt_item", null);
  				  		cur_frm.alt_list_data.push({"alt_item": item_code});
						cur_frm.render_alts_items(d, headers, cur_frm.alt_list_data)
						cur_frm.set_alt_items()
					}
				},
				get_query: () => {
					var allready_selected = Object.keys(cur_frm.alt_list_data).map(key => cur_frm.alt_list_data[key].alt_item)
					return {
						query: "erpnext.stock.doctype.item_alternative.item_alternative.get_bom_alternative_items",
						filters: {
							item_code: parent_item_code,
							exclude: allready_selected
						}
					};
				}
			},
			{
				fieldtype:'Link',
				fieldname:"add_regular_item",
				options: 'Item',
				label: __('Add Item'),
				get_query: () => {
					var allready_selected = Object.keys(cur_frm.alt_list_data).map(key => cur_frm.alt_list_data[key].alt_item)
					return {
			           filters: [
			   			['Item', 'item_code', 'not in', allready_selected] // not in!!!
			   		]
			       }
			    },
				onchange: function() {
				  var item_code = this.get_value();
				  if (item_code) {
						d.set_value("add_regular_item", null);
						cur_frm.alt_list_data.push({
							"alt_item": item_code,
						});
						cur_frm.render_alts_items(d, headers, cur_frm.alt_list_data)
						cur_frm.set_alt_items()
				  }
				}
			},
			{
				fieldtype:'HTML',
				fieldname:"alt_items",
				label: __('Alternative Items'),
			}
		],
		primary_action: function() {
			frappe.call({
				method: 'erpnext.manufacturing.doctype.bom.bom.setup_bomline_alternative_items',
				freeze: true,
				args: {
					items: cur_frm.alt_list_data,
					bom: bom,
					parent_item_code: parent_item_code
				},
				callback:function(r){
					cur_frm.render_alts_items(d, headers, cur_frm.alt_list_data)
					cur_frm.set_alt_items()
				}
			})
			this.hide();
		},
		primary_action_label: __('Update')
	});

	frappe.call({
		method: 'erpnext.manufacturing.doctype.bom.bom.get_bomline_alternative_items',
		freeze: true,
		args: {
			bom: bom,
			parent_item_code: parent_item_code
		},
		callback:function(r){
			cur_frm.alt_list_data =  r.message || [];
			cur_frm.render_alts_items(d, headers, cur_frm.alt_list_data)
			cur_frm.set_alt_items()
		}
	})
	cur_frm.remove_row = function(i){
		// remove a row
		cur_frm.alt_list_data.splice(i, 1);
		cur_frm.render_alts_items(d, headers, cur_frm.alt_list_data)
		cur_frm.set_alt_items()
	}
	d.show();
}

var toggle_operations = function(frm) {
	frm.toggle_display("operations_section", cint(frm.doc.with_operations) == 1);
};

frappe.ui.form.on("BOM", "with_operations", function(frm) {
	if(!cint(frm.doc.with_operations)) {
		frm.set_value("operations", []);
	}
	toggle_operations(frm);
});

cur_frm.cscript.image = function() {
	refresh_field("image_view");
};
