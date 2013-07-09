// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

// define defaults for purchase common
cur_frm.cscript.tname = "Supplier Quotation Item";
cur_frm.cscript.fname = "quotation_items";
cur_frm.cscript.other_fname = "purchase_tax_details";

// attach required files
wn.require('app/accounts/doctype/purchase_taxes_and_charges_master/purchase_taxes_and_charges_master.js');
wn.require('app/buying/doctype/purchase_common/purchase_common.js');

erpnext.buying.SupplierQuotationController = erpnext.buying.BuyingController.extend({
	refresh: function() {
		this._super();
		

		if (this.frm.doc.docstatus === 1) {
			cur_frm.add_custom_button("Make Purchase Order", cur_frm.cscript.make_purchase_order);
		}
	},
	
	onload_post_render: function(doc, dt, dn) {	
		var me = this;
		var callback = function(doc, dt, dn) {
			cur_frm.cscript.load_taxes(me.frm.doc);
		}
		
		// TODO: improve this
		if(this.frm.doc.__islocal) {
			if (this.frm.fields_dict.price_list_name && this.frm.doc.price_list_name) {
				this.price_list_name(callback);
			} else {
				callback(doc, dt, dn);
			}
		}
	}
	
});

var new_cscript = new erpnext.buying.SupplierQuotationController({frm: cur_frm});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new_cscript);


cur_frm.cscript.onload = function(doc, dt, dn) {
	// set missing values in parent doc
	set_missing_values(doc, {
		fiscal_year: sys_defaults.fiscal_year,
		conversion_rate: 1,
		currency: sys_defaults.currency,
		status: "Draft",
		transaction_date: get_today(),
		is_subcontracted: "No"
	});
}

cur_frm.cscript.make_purchase_order = function() {
	var new_po_name = wn.model.make_new_doc_and_get_name("Purchase Order");
	$c("dt_map", {
		"docs": wn.model.compress([locals['Purchase Order'][new_po_name]]),
		"from_doctype": cur_frm.doc.doctype,
		"to_doctype": "Purchase Order",
		"from_docname": cur_frm.doc.name,
		"from_to_list": JSON.stringify([['Supplier Quotation', 'Purchase Order'],
			['Supplier Quotation Item', 'Purchase Order Item'],
			['Purchase Taxes and Charges', 'Purchase Taxes and Charges']]),
	}, function(r, rt) { loaddoc("Purchase Order", new_po_name) });
}

cur_frm.cscript.supplier = function(doc, dt, dn) {
	if (doc.supplier) {
		get_server_fields('get_default_supplier_address',
			JSON.stringify({ supplier: doc.supplier }), '', doc, dt, dn, 1,
			function() { cur_frm.refresh(); });
	}
}

cur_frm.cscript.uom = function(doc, cdt, cdn) {
	// no need to trigger updation of stock uom, as this field doesn't exist in supplier quotation
}

cur_frm.fields_dict['quotation_items'].grid.get_field('project_name').get_query = 
	function(doc, cdt, cdn) {
		return "select `tabProject`.name from `tabProject` \
			where `tabProject`.status not in (\"Completed\", \"Cancelled\") \
			and `tabProject`.name like \"%s\" \
			order by `tabProject`.name ASC LIMIT 50";
	}

cur_frm.fields_dict['indent_no'].get_query = function(doc) {
	return "select distinct `name` from `tabMaterial Request` \
		where material_request_type='Purchase' and company = \"" + doc.company +
		"\" and `docstatus` = 1 and `status` != \"Stopped\" and \
		ifnull(`per_ordered`,0) < 99.99 and \
		%(key)s LIKE \"%s\" order by `name` desc limit 50";
}

cur_frm.cscript.supplier_address = function(doc, dt, dn) {
	if (doc.supplier) {
		get_server_fields("get_supplier_address", JSON.stringify({supplier: doc.supplier,
			address: doc.supplier_address, contact: doc.contact_person}), '', doc, dt, dn, 1);
	}
}
cur_frm.cscript.contact_person = cur_frm.cscript.supplier_address;

cur_frm.fields_dict['supplier_address'].get_query = function(doc, cdt, cdn) {
	return "SELECT name, address_line1, city FROM tabAddress WHERE supplier = \"" + doc.supplier
		+ "\" AND docstatus != 2 AND name LIKE \"%s\" ORDER BY name ASC LIMIT 50";
}

cur_frm.fields_dict['contact_person'].get_query = function(doc, cdt, cdn) {
	return "SELECT name, CONCAT(first_name, \" \", ifnull(last_name,\"\")) As FullName, \
		department, designation FROM tabContact WHERE supplier = \"" + doc.supplier 
		+"\" AND docstatus != 2 AND name LIKE \"%s\" ORDER BY name ASC LIMIT 50";
}

cur_frm.fields_dict.supplier_address.on_new = function(dn) {
	locals['Address'][dn].supplier = locals[cur_frm.doctype][cur_frm.docname].supplier;
	locals['Address'][dn].supplier_name = locals[cur_frm.doctype][cur_frm.docname].supplier_name;
}

cur_frm.fields_dict.contact_person.on_new = function(dn) {
	locals['Contact'][dn].supplier = locals[cur_frm.doctype][cur_frm.docname].supplier;
	locals['Contact'][dn].supplier_name = locals[cur_frm.doctype][cur_frm.docname].supplier_name;
}