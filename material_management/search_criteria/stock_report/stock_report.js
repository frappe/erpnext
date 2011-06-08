//233
report.customize_filters = function() {
  this.mytabs.items['Select Columns'].hide()
  this.mytabs.items['More Filters'].hide()
  this.hide_all_filters();
  this.add_filter({fieldname:'based_on', label:'Based On', fieldtype:'Select', options:'Warehouse'+NEWLINE+'Item Code',report_default:'Warehouse',ignore : 1,parent:'Stock Ledger Entry'});
  this.filter_fields_dict['Stock Ledger Entry'+FILTER_SEP +'To Posting Date'].df.filter_hide = 0;
  this.filter_fields_dict['Stock Ledger Entry'+FILTER_SEP +'Item Code'].df.filter_hide = 0;
  this.filter_fields_dict['Stock Ledger Entry'+FILTER_SEP +'Warehouse'].df.filter_hide = 0;
  this.filter_fields_dict['Stock Ledger Entry'+FILTER_SEP +'Warehouse Type'].df.filter_hide = 0;
  this.filter_fields_dict['Stock Ledger Entry'+FILTER_SEP +'From Posting Date'].df.filter_hide = 1;

  this.filter_fields_dict['Stock Ledger Entry'+FILTER_SEP +'Item Code'].df.in_first_page = 1;
  this.filter_fields_dict['Stock Ledger Entry'+FILTER_SEP +'Warehouse'].df.in_first_page = 1;
  this.filter_fields_dict['Stock Ledger Entry'+FILTER_SEP +'Based On'].df.in_first_page = 1;
  this.filter_fields_dict['Stock Ledger Entry'+FILTER_SEP +'Warehouse Type'].df.in_first_page = 1;
  this.filter_fields_dict['Stock Ledger Entry'+FILTER_SEP +'To Posting Date'].df.in_first_page = 1;
}


report.get_query = function(){
  based_on = this.filter_fields_dict['Stock Ledger Entry'+FILTER_SEP+'Based On'].get_value();
  as_on = this.filter_fields_dict['Stock Ledger Entry'+FILTER_SEP+'To Posting Date'].get_value();
  warehouse = this.filter_fields_dict['Stock Ledger Entry'+FILTER_SEP+'Warehouse'].get_value();
  warehouse_type = this.filter_fields_dict['Stock Ledger Entry'+FILTER_SEP+'Warehouse Type'].get_value();
  item_code = this.filter_fields_dict['Stock Ledger Entry'+FILTER_SEP+'Item Code'].get_value();

  cond = '';
  date_cond = '';
  tables = '';
  cols = '';
  group_by = '';
  ware_type_cond = '';
  war = '';
  if(!as_on) as_on = get_today();

  date_cond = repl(' AND `tabStock Ledger Entry`.posting_date <= "%(as_on)s" ', {as_on:as_on});

  if(warehouse_type.length > 0 && warehouse_type != ''){
    for(var i = 0; i<warehouse_type.length; i++) war += "'"+warehouse_type[i]+"',";
    ware_type_cond = repl(' AND `tabWarehouse`.warehouse_type IN (%(war)s)', {war: war.substr(0,war.length-1)})
  }
  
  if(based_on.length == 1){
    if(based_on == 'Item Code'){
      cols = '`tabItem`.name AS "Item Code", `tabItem`.item_name AS "Item Name", `tabItem`.description AS "Description", `tabItem`.stock_uom AS "Stock UOM"';
      cond = '(IFNULL(`tabItem`.`end_of_life`,"") = "" OR `tabItem`.`end_of_life` = "0000-00-00" OR `tabItem`.`end_of_life` > NOW()) AND `tabItem`.is_stock_item = "Yes"';
      if(item_code) cond += repl(' AND `tabItem`.name = %(item)s', {item:'"'+item_code+'"'});
      cond += ' AND `tabStock Ledger Entry`.item_code = `tabItem`.name'
      tables = '`tabItem`';
      group_by = '`tabStock Ledger Entry`.item_code';
    }
    else if(based_on == 'Warehouse'){
      cols = '`tabWarehouse`.name AS "Warehouse", `tabWarehouse`.warehouse_type AS "Warehouse Type"';
      cond = '`tabWarehouse`.docstatus < 2'
      if(warehouse) cond += repl(' AND `tabWarehouse`.name = %(warehouse)s', {warehouse:'"'+warehouse+'"'});
      cond += repl(' AND `tabStock Ledger Entry`.warehouse = `tabWarehouse`.name %(ware_type_cond)s', {ware_type_cond:ware_type_cond})
      tables = '`tabWarehouse`';
      group_by = '`tabStock Ledger Entry`.warehouse';
    }
  }
  else if(based_on.length == 2){
    cols = '`tabItem`.name AS "Item Code", `tabItem`.item_name AS "Item Name", `tabItem`.description AS "Description", `tabItem`.stock_uom AS "Stock UOM", `tabWarehouse`.name AS "Warehouse",  `tabWarehouse`.warehouse_type AS "Warehouse Type"';
    cond = '(IFNULL(`tabItem`.`end_of_life`,"") = "" OR `tabItem`.`end_of_life` = "0000-00-00" OR `tabItem`.`end_of_life` > NOW()) AND `tabItem`.is_stock_item = "Yes" AND `tabWarehouse`.docstatus < 2';
    if(item_code) cond += repl(" AND `tabItem`.name = %(item)s", {item:"'"+item_code+"'"});
    if(warehouse) cond += repl(" AND `tabWarehouse`.name = %(warehouse)s", {warehouse:"'"+warehouse+"'"});
    cond += repl(' AND `tabStock Ledger Entry`.item_code = `tabItem`.name AND `tabStock Ledger Entry`.warehouse = `tabWarehouse`.name %(ware_type_cond)s', {ware_type_cond:ware_type_cond})
    tables = '`tabItem`, `tabWarehouse`';
    group_by = '`tabStock Ledger Entry`.item_code, `tabStock Ledger Entry`.warehouse';
  }

  q = repl("SELECT %(cols)s FROM %(tables)s, `tabStock Ledger Entry` WHERE %(cond)s %(date_cond)s GROUP BY %(group_by)s", {cols:cols, tables:tables, cond:cond, date_cond:date_cond, group_by:group_by});
  return q;
}