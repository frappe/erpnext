cur_frm.cscript.refresh = function(doc) {
	// make sensitive fields(has_serial_no, is_stock_item, valuation_method)
	// read only if any stock ledger entry exists
	
	if ((!doc.__islocal) && (doc.is_stock_item == 'Yes')) {
		var callback = function(r, rt) {
			if (r.message == 'exists') permlevel = 1;
			else permlevel = 0;
				
			set_field_permlevel('has_serial_no', permlevel);
			set_field_permlevel('is_stock_item', permlevel);
			set_field_permlevel('valuation_method', permlevel);
		}
		$c_obj(make_doclist(doc.doctype, doc.name),'check_if_sle_exists','',callback); 
	}
}


cur_frm.fields_dict['default_bom'].get_query = function(doc) {
   //var d = locals[this.doctype][this.docname];
   return 'SELECT DISTINCT `tabBill Of Materials`.`name` FROM `tabBill Of Materials` WHERE `tabBill Of Materials`.`item` = "' + doc.item_code + '"  AND `tabBill Of Materials`.`is_active` = "No" and `tabBill Of Materials`.docstatus != 2 AND `tabBill Of Materials`.%(key)s LIKE "%s" ORDER BY `tabBill Of Materials`.`name` LIMIT 50'
}


// Expense Account
// ---------------------------------
cur_frm.fields_dict['purchase_account'].get_query = function(doc){ 
  return 'SELECT DISTINCT `tabAccount`.`name` FROM `tabAccount` WHERE `tabAccount`.`debit_or_credit`="Debit" AND `tabAccount`.`group_or_ledger`="Ledger" AND `tabAccount`.`docstatus`!=2 AND `tabAccount`.`is_pl_account` = "Yes" AND `tabAccount`.%(key)s LIKE "%s" ORDER BY `tabAccount`.`name` LIMIT 50'
}

// Income Account 
// --------------------------------
cur_frm.fields_dict['default_income_account'].get_query = function(doc) {
  return 'SELECT DISTINCT `tabAccount`.`name` FROM `tabAccount` WHERE `tabAccount`.`debit_or_credit`="Credit" AND `tabAccount`.`group_or_ledger`="Ledger" AND `tabAccount`.`is_pl_account` = "Yes" AND `tabAccount`.`docstatus`!=2 AND `tabAccount`.`account_type` ="Income Account" AND `tabAccount`.%(key)s LIKE "%s" ORDER BY `tabAccount`.`name` LIMIT 50'
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
  return 'SELECT `tabItem Group`.`name`,`tabItem Group`.`parent_item_group` FROM `tabItem Group` WHERE `tabItem Group`.`is_group` = "No" AND `tabItem Group`.`docstatus`!= 2 AND `tabItem Group`.%(key)s LIKE "%s"  ORDER BY  `tabItem Group`.`name` ASC LIMIT 50'
}

cur_frm.cscript.IGHelp = function(doc,dt,dn){
  var call_back = function(){
    var sb_obj = new SalesBrowser();        
    sb_obj.set_val('Item Group');

  }
  loadpage('Sales Browser',call_back);
}

// for description from attachment
// takes the first attachment and creates
// a table with both image and attachment in HTML
// in the "alternate_description" field
cur_frm.cscript['Add Image'] = function(doc, dt, dn) {
	if(!doc.file_list) {
		msgprint('Please attach a file first!'); 
	}
	
	var f = doc.file_list.split('\n')[0];
	var fname = f.split(',')[0];
	var fid = f.split(',')[1];
	if(!in_list(['jpg','jpeg','gif','png'], fname.split('.')[1].toLowerCase())) {
		msgprint('File must be of extension jpg, jpeg, gif or png'); return;
	}
	
	doc.description_html = repl('<table style="width: 100%; table-layout: fixed;">'+
	'<tr><td style="width:110px"><img src="%(imgurl)s" width="100px"></td>'+
	'<td>%(desc)s</td></tr>'+
	'</table>', {imgurl: wn.urllib.get_file_url(fid), desc:doc.description});
	
	refresh_field('description_html');
}

