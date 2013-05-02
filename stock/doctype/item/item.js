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

cur_frm.add_fetch("price_list_name", "currency", "ref_currency")

cur_frm.cscript.refresh = function(doc) {
	// make sensitive fields(has_serial_no, is_stock_item, valuation_method)
	// read only if any stock ledger entry exists

	cur_frm.toggle_display("naming_series", sys_defaults.item_naming_by=="Naming Series" 
		&& doc.__islocal)
	cur_frm.toggle_display("item_code", sys_defaults.item_naming_by!="Naming Series"
		&& doc.__islocal)


	if ((!doc.__islocal) && (doc.is_stock_item == 'Yes')) {
		var callback = function(r, rt) {
			var enabled = (r.message == 'exists') ? false : true;
			cur_frm.toggle_enable(['has_serial_no', 'is_stock_item', 'valuation_method'], enabled);
		}
		$c_obj(make_doclist(doc.doctype, doc.name),'check_if_sle_exists','',callback);
	}
}

cur_frm.cscript.item_code = function(doc) {
	if(!doc.item_name) cur_frm.set_value("item_name", doc.item_code);
	if(!doc.description) cur_frm.set_value("description", doc.item_code);
}

cur_frm.fields_dict['default_bom'].get_query = function(doc) {
   //var d = locals[this.doctype][this.docname];
   return 'SELECT DISTINCT `tabBOM`.`name` FROM `tabBOM` WHERE `tabBOM`.`item` = "' + doc.item_code + '"  AND ifnull(`tabBOM`.`is_active`, 0) = 0 and `tabBOM`.docstatus != 2 AND `tabBOM`.%(key)s LIKE "%s" ORDER BY `tabBOM`.`name` LIMIT 50'
}


// Expense Account
// ---------------------------------
cur_frm.fields_dict['purchase_account'].get_query = function(doc){
  return 'SELECT DISTINCT `tabAccount`.`name` FROM `tabAccount` WHERE `tabAccount`.`debit_or_credit`="Debit" AND `tabAccount`.`group_or_ledger`="Ledger" AND `tabAccount`.`docstatus`!=2 AND `tabAccount`.%(key)s LIKE "%s" ORDER BY `tabAccount`.`name` LIMIT 50'
}

// Income Account
// --------------------------------
cur_frm.fields_dict['default_income_account'].get_query = function(doc) {
  return 'SELECT DISTINCT `tabAccount`.`name` FROM `tabAccount` WHERE `tabAccount`.`debit_or_credit`="Credit" AND `tabAccount`.`group_or_ledger`="Ledger" AND `tabAccount`.`docstatus`!=2 AND `tabAccount`.`account_type` ="Income Account" AND `tabAccount`.%(key)s LIKE "%s" ORDER BY `tabAccount`.`name` LIMIT 50'
}


// Purchase Cost Center
// -----------------------------
cur_frm.fields_dict['cost_center'].get_query = function(doc) {
  return 'SELECT `tabCost Center`.`name` FROM `tabCost Center` WHERE `tabCost Center`.%(key)s LIKE "%s" AND `tabCost Center`.`group_or_ledger` = "Ledger" AND `tabCost Center`.`docstatus`!= 2 ORDER BY  `tabCost Center`.`name` ASC LIMIT 50'
}


// Sales Cost Center
// -----------------------------
cur_frm.fields_dict['default_sales_cost_center'].get_query = function(doc) {
  return 'SELECT `tabCost Center`.`name` FROM `tabCost Center` WHERE `tabCost Center`.%(key)s LIKE "%s" AND `tabCost Center`.`group_or_ledger` = "Ledger" AND `tabCost Center`.`docstatus`!= 2 ORDER BY  `tabCost Center`.`name` ASC LIMIT 50'
}


cur_frm.fields_dict['item_tax'].grid.get_field("tax_type").get_query = function(doc, cdt, cdn) {
  return 'SELECT `tabAccount`.`name` FROM `tabAccount` WHERE `tabAccount`.`account_type` in ("Tax", "Chargeable") and `tabAccount`.`docstatus` != 2 and `tabAccount`.%(key)s LIKE "%s" ORDER BY `tabAccount`.`name` DESC LIMIT 50'
}

cur_frm.cscript.tax_type = function(doc, cdt, cdn){
  var d = locals[cdt][cdn];
  get_server_fields('get_tax_rate',d.tax_type,'item_tax',doc, cdt, cdn, 1);
}


//get query select item group
cur_frm.fields_dict['item_group'].get_query = function(doc,cdt,cdn) {
  return 'SELECT `tabItem Group`.`name`,`tabItem Group`.`parent_item_group` \
		FROM `tabItem Group` WHERE `tabItem Group`.`docstatus`!= 2 AND \
		`tabItem Group`.%(key)s LIKE "%s"  ORDER BY  `tabItem Group`.`name` \
		ASC LIMIT 50'
}

// for description from attachment
// takes the first attachment and creates
// a table with both image and attachment in HTML
// in the "alternate_description" field
cur_frm.cscript.add_image = function(doc, dt, dn) {
	if(!doc.image) {
		msgprint('Please select an "Image" first');
		return;
	}

	doc.description_html = repl('<table style="width: 100%; table-layout: fixed;">'+
	'<tr><td style="width:110px"><img src="%(imgurl)s" width="100px"></td>'+
	'<td>%(desc)s</td></tr>'+
	'</table>', {imgurl: wn.utils.get_file_link(doc.image), desc:doc.description});

	refresh_field('description_html');
}
// Quotation to validation - either customer or lead mandatory
cur_frm.cscript.weight_to_validate = function(doc,cdt,cdn){

  if((doc.nett_weight || doc.gross_weight) && !doc.weight_uom)
  {
    alert('Weight is mentioned,\nPlease mention "Weight UOM" too');
    validated=0;
  }
}

cur_frm.cscript.validate = function(doc,cdt,cdn){
  cur_frm.cscript.weight_to_validate(doc,cdt,cdn);
}

cur_frm.fields_dict['ref_rate_details'].grid.onrowadd = function(doc, cdt, cdn){
	locals[cdt][cdn].ref_currency = sys_defaults.currency;
	refresh_field('ref_currency',cdn,'ref_rate_details');
}

cur_frm.fields_dict.item_customer_details.grid.get_field("customer_name").get_query = 
	erpnext.utils.customer_query;
	
cur_frm.fields_dict.item_supplier_details.grid.get_field("supplier").get_query = 
	erpnext.utils.supplier_query;

cur_frm.cscript.on_remove_attachment = function(doc) {
	// refresh image list before unsetting image
	refresh_field("image");
	if(!inList(cur_frm.fields_dict.image.df.options.split("\n"), doc.image)) {
		// if the selected image is removed from attachment, unset it
		cur_frm.set_value("image", "");
		msgprint(wn._("Attachment removed. You may need to update: ") 
			+ wn.meta.get_docfield(doc.doctype, "description_html").label);
	}
};

cur_frm.cscript.copy_from_item_group = function(doc) {
	wn.model.with_doc("Item Group", doc.item_group, function() {
		$.each(wn.model.get("Item Website Specification", {parent:doc.item_group}), 
			function(i, d) {
				var n = wn.model.add_child(doc, "Item Website Specification", 
					"item_website_specifications");
				n.label = d.label;
				n.description = d.description;
			}
		);
		cur_frm.refresh();
	});
}
