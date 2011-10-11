 

cur_frm.cscript.onload = function(){
   
  if(doc.__islocal){
    doc.parent_customer_group = 'Root';
    refresh('parent_customer_group');
  }
}

cur_frm.cscript.refresh = function(doc, cdt, cdn) {
   
}

//get query select Customer Group
cur_frm.fields_dict['parent_customer_group'].get_query = function(doc,cdt,cdn) {
  return 'SELECT `tabCustomer Group`.`name`,`tabCustomer Group`.`parent_customer_group` FROM `tabCustomer Group` WHERE `tabCustomer Group`.`is_group` = "Yes" AND `tabCustomer Group`.`docstatus`!= 2 AND `tabCustomer Group`.%(key)s LIKE "%s" ORDER BY  `tabCustomer Group`.`name` ASC LIMIT 50';
}