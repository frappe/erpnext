 

cur_frm.cscript.refresh = function(doc, cdt, cdn) {
   
}

cur_frm.cscript.onload = function(){
   
  if(doc.__islocal){
    doc.parent_territory = 'All Territories';
    refresh('parent_territory');
  }
}


//get query select territory
cur_frm.fields_dict['parent_territory'].get_query = function(doc,cdt,cdn) {
  return 'SELECT `tabTerritory`.`name`,`tabTerritory`.`parent_territory` FROM `tabTerritory` WHERE `tabTerritory`.`is_group` = "Yes" AND `tabTerritory`.`docstatus`!= 2 AND (`tabTerritory`.`rgt` > '+doc.rgt+' or `tabTerritory`.`lft` < '+doc.lft+') AND `tabTerritory`.`name` !="'+doc.territory_name+'" AND `tabTerritory`.%(key)s LIKE "%s" ORDER BY  `tabTerritory`.`name` ASC LIMIT 50';
}


// ******************** ITEM Group ******************************** 
cur_frm.fields_dict['target_details'].grid.get_field("item_group").get_query = function(doc, cdt, cdn) {
  return 'SELECT `tabItem Group`.`name`,`tabItem Group`.`parent_item_group` FROM `tabItem Group` WHERE `tabItem Group`.is_group="No" AND `tabItem Group`.docstatus != 2 AND `tabItem Group`.%(key)s LIKE "%s" LIMIT 50'
}

cur_frm.cscript.TerritoryHelp = function(doc,dt,dn){
  var call_back = function(){
    var sb_obj = new SalesBrowser();        
    sb_obj.set_val('Territory');

  }
  loadpage('Sales Browser',call_back);
  
}