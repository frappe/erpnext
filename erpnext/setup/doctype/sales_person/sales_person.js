
cur_frm.cscript.refresh = function(doc, cdt, cdn) {
}

cur_frm.cscript.onload = function(){
  if(doc.__islocal){
    doc.parent_sales_person = 'Root';
    refresh('parent_sales_person');
  }
}
cur_frm.cscript.country = function(doc, cdt, cdn) {
  var mydoc=doc;
  $c('runserverobj', args={'method':'check_state', 'docs':compress_doclist([doc])},
    function(r,rt){
      if(r.message) {
        var doc = locals[mydoc.doctype][mydoc.name];
        doc.state = '';
        get_field(doc.doctype, 'state' , doc.name).options = r.message;
        refresh_field('state');
      }
    }  
  );
}

cur_frm.cscript.TreePage = function(nm){
  var call_back = function(){
    var sb_obj = new SalesBrowser();        
    sb_obj.set_val(nm);

  }
  loadpage('Sales Browser',call_back);

}

//get query select sales person
cur_frm.fields_dict['parent_sales_person'].get_query = function(doc,cdt,cdn) {
  return 'SELECT `tabSales Person`.`name`,`tabSales Person`.`parent_sales_person` FROM `tabSales Person` WHERE `tabSales Person`.`is_group` = "Yes" AND `tabSales Person`.`docstatus`!= 2 AND (`tabSales Person`.`rgt` > '+doc.rgt+' or `tabSales Person`.`lft` < '+doc.lft+') AND `tabSales Person`.`name` !="'+doc.sales_person_name+'" AND `tabSales Person`.%(key)s LIKE "%s" ORDER BY  `tabSales Person`.`name` ASC LIMIT 50';
}

//get query select Territory
cur_frm.fields_dict['territory'].get_query = function(doc,cdt,cdn) {
  return 'SELECT `tabTerritory`.`name` FROM `tabTerritory` WHERE `tabTerritory`.`is_group` = "No" AND `tabTerritory`.`docstatus`!= 2 AND `tabTerritory`.%(key)s LIKE "%s" ORDER BY  `tabTerritory`.`name` ASC LIMIT 50';
}

// ******************** ITEM Group ******************************** 
cur_frm.fields_dict['target_details'].grid.get_field("item_group").get_query = function(doc, cdt, cdn) {
  return 'SELECT `tabItem Group`.name FROM `tabItem Group` WHERE `tabItem Group`.is_group="No" AND `tabItem Group`.docstatus != 2 AND `tabItem Group`.%(key)s LIKE "%s" LIMIT 50'
}
