// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt
wn.provide("erpnext");

$.extend(erpnext, {
	get_currency: function(company) {
		if(!company && cur_frm)
			company = cur_frm.doc.company;
		if(company)
			return wn.model.get_doc(":Company", company).default_currency || wn.boot.sysdefaults.currency;
		else
			return wn.boot.sysdefaults.currency;
	},
	
	hide_naming_series: function() {
		if(cur_frm.fields_dict.naming_series && !wn.meta.get_docfield(cur_frm.doctype, "naming_series")) {
			cur_frm.toggle_display("naming_series", cur_frm.doc.__islocal?true:false);
		}
	},
	
	hide_company: function() {
		if(cur_frm.fields_dict.company) {
			var companies = Object.keys(locals[":Company"] || {});
			if(companies.length === 1) {
				if(!cur_frm.doc.company) cur_frm.set_value("company", companies[0]);
				cur_frm.toggle_display("company", false);
			}
		}
	},
	
	add_applicable_territory: function() {
		if(cur_frm.doc.__islocal && 
			wn.model.get_doclist(cur_frm.doc.doctype, cur_frm.doc.name).length === 1) {
				var territory = wn.model.add_child(cur_frm.doc, "Applicable Territory", 
					"valid_for_territories");
				territory.territory = wn.defaults.get_default("territory");
		}
	},
	
	setup_serial_no: function(grid_row) {
		if(!grid_row.fields_dict.serial_no || 
			grid_row.fields_dict.serial_no.get_status()!=="Write") return;
		
		var $btn = $('<button class="btn btn-sm btn-default">'+wn._("Add Serial No")+'</button>')
			.appendTo($("<div>")
				.css({"margin-bottom": "10px", "margin-left": "15px"})
				.appendTo(grid_row.fields_dict.serial_no.$wrapper));
				
		$btn.on("click", function() {
			var d = new wn.ui.Dialog({
				title: wn._("Add Serial No"),
				fields: [
					{
						"fieldtype": "Link",
						"options": "Serial No",
						"label": wn._("Serial No"),
						"get_query": {
							item_code: grid_row.doc.item_code,
							warehouse: grid_row.doc.warehouse
						}
					},
					{
						"fieldtype": "Button",
						"label": wn._("Add")
					}
				]
			});
			
			d.get_input("add").on("click", function() {
				var serial_no = d.get_value("serial_no");
				if(serial_no) {
					var val = (grid_row.doc.serial_no || "").split("\n").concat([serial_no]).join("\n");
					grid_row.fields_dict.serial_no.set_model_value(val.trim());
				}
				d.hide();
				return false;
			});
			
			d.show();
		});
	}
});