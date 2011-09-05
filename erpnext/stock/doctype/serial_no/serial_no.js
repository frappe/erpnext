// ************************************** onload ****************************************************
cur_frm.cscript.onload = function(doc, cdt, cdn) {
  if(!doc.status) set_multiple(cdt, cdn, {status:'In Store'});
  if(doc.__islocal) hide_field(['supplier_name','address_display'])
}


// ************************************** refresh ***************************************************
cur_frm.cscript.refresh = function(doc, cdt, cdn) {
  if(!doc.__islocal) {
    flds = ['item_code', 'warehouse', 'purchase_document_type', 'purchase_document_no', 'purchase_date', 'purchase_time', 'purchase_rate', 'supplier']
    for(i=0;i<flds.length;i++) 
      set_field_permlevel(flds[i], 1);
  }
}


// ************************************** triggers **************************************************

// item details
// -------------
cur_frm.add_fetch('item_code', 'item_name', 'item_name')
cur_frm.add_fetch('item_code', 'item_group', 'item_group')
cur_frm.add_fetch('item_code', 'brand', 'brand')
cur_frm.add_fetch('item_code', 'description', 'description')
cur_frm.add_fetch('item_code', 'warranty_period', 'warranty_period')

// customer
// ---------
cur_frm.add_fetch('customer', 'customer_name', 'customer_name')
cur_frm.add_fetch('customer', 'address', 'delivery_address')
cur_frm.add_fetch('customer', 'territory', 'territory')

// territory
// ----------
cur_frm.fields_dict['territory'].get_query = function(doc,cdt,cdn) {
  return 'SELECT `tabTerritory`.`name`,`tabTerritory`.`parent_territory` FROM `tabTerritory` WHERE `tabTerritory`.`is_group` = "No" AND `tabTerritory`.`docstatus`!= 2 AND `tabTerritory`.%(key)s LIKE "%s"  ORDER BY  `tabTerritory`.`name` ASC LIMIT 50';
}

// Supplier
//-------------
cur_frm.cscript.supplier = function(doc,dt,dn) {
  if(doc.supplier) get_server_fields('get_default_supplier_address', JSON.stringify({supplier: doc.supplier}),'', doc, dt, dn, 1);
  if(doc.supplier) unhide_field(['supplier_name','address_display']);
}
