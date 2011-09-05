cur_frm.cscript.onload = function(doc, cdt, cdn) {
  if (!doc.posting_date) doc.posting_date = dateutil.obj_to_str(new Date());
  if (!doc.transfer_date) doc.transfer_date = dateutil.obj_to_str(new Date());
  cfn_set_fields(doc, cdt, cdn);
}


var cfn_set_fields = function(doc, cdt, cdn) {
  lst = ['supplier','supplier_name','supplier_address','customer','customer_name','customer_address']; 
  if (doc.purpose == 'Production Order'){
    unhide_field(['production_order', 'process', 'Get Items']);
    hide_field(['from_warehouse', 'to_warehouse','purchase_receipt_no','delivery_note_no', 'sales_invoice_no','Warehouse HTML']);
    doc.from_warehouse = '';
    doc.to_warehosue = '';
    if (doc.process == 'Backflush'){
      unhide_field('fg_completed_qty');
    }
    else{
      hide_field('fg_completed_qty');
      doc.fg_completed_qty = 0;
    }
  }
  else{
    unhide_field(['from_warehouse', 'to_warehouse']);
    hide_field(['production_order', 'process', 'Get Items', 'fg_completed_qty','purchase_receipt_no','delivery_note_no', 'sales_invoice_no']);
    hide_field(lst);
    doc.production_order = '';
    doc.process = '';
    doc.fg_completed_qty = 0;
  }
  
 
  if(doc.purpose == 'Purchase Return'){
    doc.customer=doc.customer_name = doc.customer_address=doc.delivery_note_no=doc.sales_invoice_no='';
    hide_field(lst);
    unhide_field(['supplier','supplier_name','supplier_address','purchase_receipt_no']);
  }
  if(doc.purpose == 'Sales Return'){
    doc.supplier=doc.supplier_name = doc.supplier_address=doc.purchase_receipt_no='';
    hide_field(lst);
    unhide_field(['customer','customer_name','customer_address','delivery_note_no', 'sales_invoice_no']);
  } else{
    doc.customer=doc.customer_name=doc.customer_address=doc.delivery_note_no=doc.sales_invoice_no=doc.supplier=doc.supplier_name = doc.supplier_address=doc.purchase_receipt_no='';
  }
  refresh_many(lst);
}

cur_frm.cscript.delivery_note_no = function(doc,cdt,cdn){
  if(doc.delivery_note_no) get_server_fields('get_cust_values','','',doc,cdt,cdn,1);
}

cur_frm.cscript.sales_invoice_no = function(doc,cdt,cdn){
  if(doc.sales_invoice_no) get_server_fields('get_cust_values','','',doc,cdt,cdn,1);
}

cur_frm.cscript.customer = function(doc,cdt,cdn){
  if(doc.customer)  get_server_fields('get_cust_addr','','',doc,cdt,cdn,1);
}

cur_frm.cscript.purchase_receipt_no = function(doc,cdt,cdn){
  if(doc.purchase_receipt_no)  get_server_fields('get_supp_values','','',doc,cdt,cdn,1);
}

cur_frm.cscript.supplier = function(doc,cdt,cdn){
  if(doc.supplier)  get_server_fields('get_supp_addr','','',doc,cdt,cdn,1);

}

cur_frm.fields_dict['production_order'].get_query = function(doc) {
   return 'SELECT DISTINCT `tabProduction Order`.`name` FROM `tabProduction Order` WHERE `tabProduction Order`.`docstatus` = 1 AND `tabProduction Order`.`qty` > ifnull(`tabProduction Order`.`produced_qty`,0) AND `tabProduction Order`.`name` like "%s" ORDER BY `tabProduction Order`.`name` DESC LIMIT 50';
}

cur_frm.cscript.purpose = function(doc, cdt, cdn) {
  cfn_set_fields(doc, cdt, cdn);
}


cur_frm.cscript.process = function(doc, cdt, cdn) {
  cfn_set_fields(doc, cdt, cdn);
}

//
// item code - only if quantity present in source warehosue
//
var fld = cur_frm.fields_dict['mtn_details'].grid.get_field('item_code');
fld.query_description = "If Source Warehouse is selected, only items present in the warehouse with actual qty > 0 will be selected"
fld.get_query = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
		
	if(d.s_warehouse) {
		return 'SELECT tabItem.name, tabItem.description, tabBin.actual_qty '
		+'FROM tabItem, tabBin '
		+'WHERE tabItem.name = tabBin.item_code '
		+'AND ifnull(`tabBin`.`actual_qty`,0) > 0 '
		+'AND tabBin.warehouse="'+ d.s_warehouse +'" '
		+'AND tabItem.docstatus < 2 '
		+'AND tabItem.%(key)s LIKE "%s" '
		+'ORDER BY tabItem.name ASC '
		+'LIMIT 50'
	} else {
		return 'SELECT tabItem.name, tabItem.description '
		+'FROM tabItem '
		+'WHERE tabItem.docstatus < 2 '
		+'AND tabItem.%(key)s LIKE "%s" '
		+'ORDER BY tabItem.name ASC '
		+'LIMIT 50'
	}
}

//
// copy over source and target warehouses
//
cur_frm.fields_dict['mtn_details'].grid.onrowadd = function(doc, cdt, cdn){
	var d = locals[cdt][cdn];
	if(!d.s_warehouse && doc.from_warehouse) {
		d.s_warehouse = doc.from_warehouse
		refresh_field('s_warehouse', cdn, 'mtn_details')
	}
	if(!d.t_warehouse && doc.to_warehouse) {
		d.t_warehouse = doc.to_warehouse
		refresh_field('t_warehouse', cdn, 'mtn_details')
	}
}

//========================= Overloaded query for link batch_no =============================================================
cur_frm.fields_dict['mtn_details'].grid.get_field('batch_no').get_query= function(doc, cdt, cdn) {
  var d = locals[cdt][cdn];
  if(d.item_code){
    return "SELECT tabBatch.name, tabBatch.description FROM tabBatch WHERE tabBatch.docstatus != 2 AND tabBatch.item = '"+ d.item_code +"' AND `tabBatch`.`name` like '%s' ORDER BY `tabBatch`.`name` DESC LIMIT 50"
  }
  else{
    alert("Please enter Item Code.");
  }
}

//==================================================================================================================

cur_frm.cscript.item_code = function(doc, cdt, cdn) {
  var d = locals[cdt][cdn];
  // get values
  args = {
  	'item_code'		: d.item_code,
  	'warehouse'		: cstr(d.s_warehouse),
  	'transfer_qty'	: d.transfer_qty,
  	'serial_no'		: d.serial_no
  };
  get_server_fields('get_item_details',JSON.stringify(args),'mtn_details',doc,cdt,cdn,1);
}

//==================================================================================================================

cur_frm.cscript.transfer_qty = function(doc,cdt,cdn) {
  var d = locals[cdt][cdn];
  if (doc.from_warehouse && (flt(d.transfer_qty) > flt(d.actual_qty))) {
    alert("Transfer Quantity is more than Available Qty");
  }
}


//==================================================================================================================

cur_frm.cscript.qty = function(doc, cdt, cdn) {
  var d = locals[cdt][cdn];
  set_multiple('Stock Entry Detail', d.name, {'transfer_qty': flt(d.qty) * flt(d.conversion_factor)}, 'mtn_details');
  refresh_field('mtn_details');
}

//==================================================================================================================

cur_frm.cscript.uom = function(doc, cdt, cdn) {
  var d = locals[cdt][cdn];
  if(d.uom && d.item_code){
    var arg = {'item_code':d.item_code, 'uom':d.uom, 'qty':d.qty}
    get_server_fields('get_uom_details',JSON.stringify(arg),'mtn_details', doc, cdt, cdn, 1);
  }
}

//==================================================================================================================
//validate
cur_frm.cscript.validate = function(doc, cdt, cdn) {
  cur_frm.cscript.validate_items(doc);
}

//==================================================================================================================
//validate items
cur_frm.cscript.validate_items = function(doc) {
  cl =  getchildren('Stock Entry Detail',doc.name,'mtn_details');
  if (!cl.length) {
    alert("Item table can not be blank");
    validated = false;
  }
}
