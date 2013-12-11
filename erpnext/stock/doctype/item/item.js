// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.refresh = function(doc) {
	// make sensitive fields(has_serial_no, is_stock_item, valuation_method)
	// read only if any stock ledger entry exists

	cur_frm.cscript.make_dashboard()
	erpnext.hide_naming_series();
		
	if(!doc.__islocal && doc.show_in_website) {
		cur_frm.appframe.add_button("View In Website", function() {
			window.open(doc.page_name);
		}, "icon-globe");
	}
	cur_frm.cscript.edit_prices_button();

	if (!doc.__islocal && doc.is_stock_item == 'Yes') {
		cur_frm.toggle_enable(['has_serial_no', 'is_stock_item', 'valuation_method'],
			doc.__sle_exists=="exists" ? false : true);
	}
}

cur_frm.cscript.make_dashboard = function() {
	cur_frm.dashboard.reset();
	if(cur_frm.doc.__islocal) 
		return;
}

cur_frm.cscript.edit_prices_button = function() {
	cur_frm.add_custom_button("Add / Edit Prices", function() {
		wn.route_options = {
			"item_code": cur_frm.doc.name
		};
		wn.set_route("Report", "Item Price");
	}, "icon-money");
}

cur_frm.cscript.item_code = function(doc) {
	if(!doc.item_name) cur_frm.set_value("item_name", doc.item_code);
	if(!doc.description) cur_frm.set_value("description", doc.item_code);
}

cur_frm.fields_dict['default_bom'].get_query = function(doc) {
   //var d = locals[this.doctype][this.docname];
    return{
   		filters:{
   			'item': doc.item_code,
   			'is_active': 0
   		}
   }
}


// Expense Account
// ---------------------------------
cur_frm.fields_dict['purchase_account'].get_query = function(doc){
	return{
		filters:{
			'debit_or_credit': "Debit",
			'group_or_ledger': "Ledger"
		}
	}
}

// Income Account
// --------------------------------
cur_frm.fields_dict['default_income_account'].get_query = function(doc) {
	return{
		filters:{
			'debit_or_credit': "Credit",
			'group_or_ledger': "Ledger",
			'account_type': "Income Account"
		}
	}
}


// Purchase Cost Center
// -----------------------------
cur_frm.fields_dict['cost_center'].get_query = function(doc) {
	return{
		filters:{ 'group_or_ledger': "Ledger" }
	}
}


// Sales Cost Center
// -----------------------------
cur_frm.fields_dict['default_sales_cost_center'].get_query = function(doc) {
	return{
		filters:{ 'group_or_ledger': "Ledger" }
	}
}


cur_frm.fields_dict['item_tax'].grid.get_field("tax_type").get_query = function(doc, cdt, cdn) {
	return{
		filters:[
			['Account', 'account_type', 'in', 'Tax, Chargeable'],
			['Account', 'docstatus', '!=', 2]
		]
	}
}

cur_frm.cscript.tax_type = function(doc, cdt, cdn){
  var d = locals[cdt][cdn];
  return get_server_fields('get_tax_rate',d.tax_type,'item_tax',doc, cdt, cdn, 1);
}


//get query select item group
cur_frm.fields_dict['item_group'].get_query = function(doc,cdt,cdn) {
	return {
		filters: [
			['Item Group', 'docstatus', '!=', 2]
		]
	}
}

// for description from attachment
// takes the first attachment and creates
// a table with both image and attachment in HTML
// in the "alternate_description" field
cur_frm.cscript.add_image = function(doc, dt, dn) {
	if(!doc.image) {
		msgprint(wn._('Please select an "Image" first'));
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
    alert(wn._('Weight is mentioned,\nPlease mention "Weight UOM" too'));
    validated=0;
  }
}

cur_frm.cscript.validate = function(doc,cdt,cdn){
  cur_frm.cscript.weight_to_validate(doc,cdt,cdn);
}

cur_frm.fields_dict.item_customer_details.grid.get_field("customer_name").get_query = 
function(doc,cdt,cdn) {
		return{	query:"controllers.queries.customer_query" } }
	
cur_frm.fields_dict.item_supplier_details.grid.get_field("supplier").get_query = 
	function(doc,cdt,cdn) {
		return{ query:"controllers.queries.supplier_query" } }

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

cur_frm.cscript.image = function() {
	refresh_field("image_view");
	
	if(!cur_frm.doc.description_html) {
		cur_frm.cscript.add_image(cur_frm.doc);
	} else {
		msgprint(wn._("You may need to update: ") + 
			wn.meta.get_docfield(cur_frm.doc.doctype, "description_html").label);
	}
}