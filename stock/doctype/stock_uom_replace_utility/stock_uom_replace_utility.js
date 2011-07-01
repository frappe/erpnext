cur_frm.fields_dict['item_code'].get_query = function(doc) {
  return 'SELECT DISTINCT `tabItem`.`name`, `tabItem`.description FROM `tabItem` WHERE (IFNULL(`tabItem`.`end_of_life`,"") = "" OR `tabItem`.`end_of_life` ="0000-00-00" OR `tabItem`.`end_of_life` > NOW()) AND `tabItem`.`%(key)s` like "%s" ORDER BY `tabItem`.`name` LIMIT 50';
}

//==================== Get Items Stock UOM =====================================================
cur_frm.cscript.item_code = function(doc,cdt,cdn) {
 if (doc.item_code) {
    get_server_fields('get_stock_uom', doc.item_code, '', doc, cdt, cdn, 1);
  }
}