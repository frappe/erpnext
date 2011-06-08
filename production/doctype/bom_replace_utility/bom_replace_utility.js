
// Get Query functions 
cur_frm.fields_dict['s_bom'].get_query = function(doc) {
  return 'SELECT `tabBill Of Materials`.`name` FROM `tabBill Of Materials` WHERE `tabBill Of Materials`.`docstatus` = 1 AND `tabBill Of Materials`.%(key)s LIKE "%s" ORDER BY `tabBill Of Materials`.`name` DESC LIMIT 50';
}

cur_frm.fields_dict['r_bom'].get_query = function(doc) {
  return 'SELECT `tabBill Of Materials`.`name` FROM `tabBill Of Materials` WHERE `tabBill Of Materials`.`docstatus` = 1 and `tabBill Of Materials`.%(key)s LIKE "%s" ORDER BY `tabBill Of Materials`.`name` DESC LIMIT 50';
}

cur_frm.fields_dict['s_item'].get_query = function(doc) {
  return 'SELECT DISTINCT `tabItem`.name FROM `tabItem` WHERE (IFNULL(`tabItem`.`end_of_life`,"") = "" OR `tabItem`.`end_of_life` ="0000-00-00" OR `tabItem`.`end_of_life` > NOW()) AND (`tabItem`.is_purchase_item = "Yes" OR`tabItem`.is_sub_contracted_item = "Yes") AND tabItem.%(key)s LIKE "%s" ORDER BY `tabItem`.item_code LIMIT 50';
}

cur_frm.fields_dict['r_item'].get_query = function(doc) {
  return 'SELECT DISTINCT `tabItem`.name FROM `tabItem` WHERE (IFNULL(`tabItem`.`end_of_life`,"") = "" OR `tabItem`.`end_of_life` ="0000-00-00" OR `tabItem`.`end_of_life` > NOW()) AND (`tabItem`.is_purchase_item = "Yes" OR`tabItem`.is_sub_contracted_item = "Yes") AND tabItem.%(key)s LIKE "%s" ORDER BY `tabItem`.item_code LIMIT 50';
}

// Client Triggers

