 

cur_frm.cscript.onload = function(){
   
  if(doc.__islocal){
    doc.parent_item_group = 'Root';
    refresh('parent_item_group');
  }
}

//get query select item group
cur_frm.fields_dict['parent_item_group'].get_query = function(doc,cdt,cdn) {
  return 'SELECT `tabItem Group`.`name`,`tabItem Group`.`parent_item_group` FROM `tabItem Group` WHERE `tabItem Group`.`is_group` = "Yes" AND  `tabItem Group`.`docstatus`!= 2 AND (`tabItem Group`.`rgt` > '+doc.rgt+' or `tabItem Group`.`lft` < '+doc.lft+') AND `tabItem Group`.`name` !="'+doc.item_group_name+'" AND `tabItem Group`.%(key)s LIKE "%s" ORDER BY  `tabItem Group`.`name` ASC LIMIT 50';
}

cur_frm.cscript.refresh = function(doc, cdt, cdn) {
   
}