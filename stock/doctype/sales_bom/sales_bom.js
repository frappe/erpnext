 

cur_frm.cscript.onload = function(doc, cdt, cdn) {
    
  if(!doc.price_list) set_multiple(cdt,cdn,{price_list:sys_defaults.price_list_name});
}

cur_frm.cscript.refresh = function(doc, cdt, cdn) {
   
}

/* Get Item Code */
cur_frm.cscript.item_code = function(doc, dt, dn) {
  var d = locals[dt][dn];
  if (d.item_code){
    get_server_fields('get_item_details', d.item_code, 'sales_bom_items', doc ,dt, dn, 1);
  }
}

cur_frm.cscript.price_list = function(doc, cdt, cdn) {
  $c_obj(make_doclist(cdt,cdn), 'get_rates', '', function(r,rt){refresh_field('sales_bom_items');});
}

cur_frm.cscript.currency = function(doc, cdt, cdn) {
  $c_obj(make_doclist(cdt,cdn), 'get_rates', '', function(r,rt){refresh_field('sales_bom_items');});
}

cur_frm.cscript['Find Sales BOM'] = function(doc, dt, dn) {
  $c_obj(make_doclist(dt,dn), 'check_duplicate', 1, '');
}