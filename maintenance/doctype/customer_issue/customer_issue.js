cur_frm.cscript.onload = function(doc,cdt,cdn){
  if(!doc.status) set_multiple(dt,dn,{status:'Open'});  
  if(doc.__islocal){    
    hide_field(['customer_address','contact_person','customer_name','address_display','contact_display','contact_mobile','contact_email','territory','customer_group']);
  }   
}

cur_frm.cscript.refresh = function(doc,ct,cdn){
  if(!doc.docstatus) hide_field('Make Maintenance Visit');
  else if(doc.docstatus && (doc.status == 'Open' || doc.status == 'Work In Progress')) unhide_field('Make Maintenance Visit');
}


//customer
cur_frm.cscript.customer = function(doc,dt,dn) {
  var callback = function(r,rt) {
      var doc = locals[cur_frm.doctype][cur_frm.docname];
      cur_frm.refresh();
  }   

  if(doc.customer) $c_obj(make_doclist(doc.doctype, doc.name), 'get_default_customer_address', '', callback);
  if(doc.customer) unhide_field(['customer_address','contact_person','customer_name','address_display','contact_display','contact_mobile','contact_email','territory','customer_group']);
}

cur_frm.cscript.customer_address = cur_frm.cscript.contact_person = function(doc,dt,dn) {    
  if(doc.customer) get_server_fields('get_customer_address', JSON.stringify({customer: doc.customer, address: doc.customer_address, contact: doc.contact_person}),'', doc, dt, dn, 1);
}

cur_frm.fields_dict.customer_address.on_new = function(dn) {
  locals['Address'][dn].customer = locals[cur_frm.doctype][cur_frm.docname].customer;
  locals['Address'][dn].customer_name = locals[cur_frm.doctype][cur_frm.docname].customer_name;
}

cur_frm.fields_dict.contact_person.on_new = function(dn) {
  locals['Contact'][dn].customer = locals[cur_frm.doctype][cur_frm.docname].customer;
  locals['Contact'][dn].customer_name = locals[cur_frm.doctype][cur_frm.docname].customer_name;
}

cur_frm.fields_dict['customer_address'].get_query = function(doc, cdt, cdn) {
  return 'SELECT name,address_line1,city FROM tabAddress WHERE customer = "'+ doc.customer +'" AND docstatus != 2 AND name LIKE "%s" ORDER BY name ASC LIMIT 50';
}

cur_frm.fields_dict['contact_person'].get_query = function(doc, cdt, cdn) {
  return 'SELECT name,CONCAT(first_name," ",ifnull(last_name,"")) As FullName,department,designation FROM tabContact WHERE customer = "'+ doc.customer +'" AND docstatus != 2 AND name LIKE "%s" ORDER BY name ASC LIMIT 50';
}




cur_frm.cscript['Make Maintenance Visit'] = function(doc, cdt, cdn) {
  if (doc.docstatus == 1) { 
    $c_obj(make_doclist(doc.doctype, doc.name),'check_maintenance_visit','',
      function(r,rt){
        if(r.message == 'No'){
          n = createLocal("Maintenance Visit");
          $c('dt_map', args={
                  'docs':compress_doclist([locals["Maintenance Visit"][n]]),
                  'from_doctype':'Customer Issue',
                  'to_doctype':'Maintenance Visit',
                  'from_docname':doc.name,
            'from_to_list':"[['Customer Issue', 'Maintenance Visit'], ['Customer Issue', 'Maintenance Visit Detail']]"
          }
          , function(r,rt) {
            loaddoc("Maintenance Visit", n);
          }
          );
        }
        else{
          msgprint("You have already completed maintenance against this Customer Issue");
        }
      }
    );
  }
}

// ----------
// serial no
// ----------

cur_frm.fields_dict['serial_no'].get_query = function(doc, cdt, cdn) {
  var cond = '';
  if(doc.item_code) cond = ' AND `tabSerial No`.item_code = "'+ doc.item_code +'"';
  return 'SELECT `tabSerial No`.name, `tabSerial No`.description FROM `tabSerial No` WHERE `tabSerial No`.docstatus != 2 AND `tabSerial No`.name LIKE "%s" '+cond+' ORDER BY `tabSerial No`.name ASC LIMIT 50';
}

cur_frm.add_fetch('serial_no', 'item_code', 'item_code');
cur_frm.add_fetch('serial_no', 'item_name', 'item_name');
cur_frm.add_fetch('serial_no', 'description', 'description');
cur_frm.add_fetch('serial_no', 'maintenance_status', 'warranty_amc_status');
cur_frm.add_fetch('serial_no', 'warranty_expiry_date', 'warranty_expiry_date');
cur_frm.add_fetch('serial_no', 'amc_expiry_date', 'amc_expiry_date');
cur_frm.add_fetch('serial_no', 'customer', 'customer');
cur_frm.add_fetch('serial_no', 'customer_name', 'customer_name');
cur_frm.add_fetch('serial_no', 'delivery_address', 'customer_address');

// ----------
// item code
// ----------
cur_frm.fields_dict['item_code'].get_query = function(doc, cdt, cdn) {
  if(doc.serial_no){
    return 'SELECT `tabSerial No`.item_code, `tabSerial No`.description FROM `tabSerial No` WHERE `tabSerial No`.docstatus != 2 AND `tabSerial No`.name = "'+ doc.serial_no +'" AND `tabSerial No`.item_code LIKE "%s" ORDER BY `tabSerial No`.item_code ASC LIMIT 50';
  }
  else{
    return 'SELECT `tabItem`.name, `tabItem`.item_name, `tabItem`.description FROM `tabItem` WHERE `tabItem`.docstatus != 2 AND `tabItem`.name LIKE "%s" ORDER BY `tabItem`.name ASC LIMIT 50';
  }
}

cur_frm.add_fetch('item_code', 'item_name', 'item_name');
cur_frm.add_fetch('item_code', 'description', 'description');


//get query select Territory
//=======================================================================================================================
cur_frm.fields_dict['territory'].get_query = function(doc,cdt,cdn) {
  return 'SELECT `tabTerritory`.`name`,`tabTerritory`.`parent_territory` FROM `tabTerritory` WHERE `tabTerritory`.`is_group` = "No" AND `tabTerritory`.`docstatus`!= 2 AND `tabTerritory`.%(key)s LIKE "%s"  ORDER BY  `tabTerritory`.`name` ASC LIMIT 50';
}
