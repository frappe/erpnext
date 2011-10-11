report.customize_filters = function() {
  //hide all filters
  //------------------------------------------------
  this.hide_all_filters();

  //add filters
  //------------------------------------------------ 
  this.add_filter({fieldname:'based_on', label:'Based On', fieldtype:'Select', options:'Purchase Order'+NEWLINE+'Purchase Invoice'+NEWLINE+'Purchase Receipt',report_default:'Purchase Order',ignore : 1,parent:'Purchase Order', single_select:1});

  this.add_filter({fieldname:'purchase_order', label:'Purchase Order', fieldtype:'Link', options:'Purchase Order', ignore : 1, parent:'Purchase Order'});
  this.add_filter({fieldname:'purchase_receipt', label:'Purchase Receipt',fieldtype:'Link', options:'Purchase Receipt',ignore : 1, parent:'Purchase Order'});
  this.add_filter({fieldname:'purchase_invoice', label:'Purchase Invoice',fieldtype:'Link', options:'Purchase Invoice',ignore : 1, parent:'Purchase Order'});  

  //unhide filters
  //------------------------------------------------    
  this.filter_fields_dict['Purchase Order'+FILTER_SEP +'Project Name'].df.filter_hide = 0;
  this.filter_fields_dict['Purchase Order'+FILTER_SEP +'Company'].df.filter_hide = 0;
  this.filter_fields_dict['Purchase Order'+FILTER_SEP +'Fiscal Year'].df.filter_hide = 0;  

  //move filter field in first page
  //------------------------------------------------    
  this.filter_fields_dict['Purchase Order'+FILTER_SEP +'Based On'].df.in_first_page = 1;
  this.filter_fields_dict['Purchase Order'+FILTER_SEP +'Project Name'].df.in_first_page = 1;
  this.filter_fields_dict['Purchase Order'+FILTER_SEP +'Purchase Order'].df.in_first_page = 1;
  this.filter_fields_dict['Purchase Order'+FILTER_SEP +'Purchase Invoice'].df.in_first_page = 1;   
  this.filter_fields_dict['Purchase Order'+FILTER_SEP +'Purchase Receipt'].df.in_first_page = 1;   
  
  // default values
  //------------------------------------------------    
  this.filter_fields_dict['Purchase Order'+FILTER_SEP +'Company'].df['report_default'] = sys_defaults.company;
  this.filter_fields_dict['Purchase Order'+FILTER_SEP +'Fiscal Year'].df['report_default'] = sys_defaults.fiscal_year;
}

//hide select columns field
//------------------------------------------------
this.mytabs.items['Select Columns'].hide();


report.get_query = function() {

  //get filter values
  based_on = this.filter_fields_dict['Purchase Order'+FILTER_SEP+'Based On'].get_value();   
  purchase_order = this.filter_fields_dict['Purchase Order'+FILTER_SEP+'Purchase Order'].get_value();
  purchase_invoice = this.filter_fields_dict['Purchase Order'+FILTER_SEP+'Purchase Invoice'].get_value();      
  purchase_receipt = this.filter_fields_dict['Purchase Order'+FILTER_SEP+'Purchase Receipt'].get_value();      
  project_name = this.filter_fields_dict['Purchase Order'+FILTER_SEP+'Project Name'].get_value();   
  company = this.filter_fields_dict['Purchase Order'+FILTER_SEP+'Company'].get_value();      
  fy = this.filter_fields_dict['Purchase Order'+FILTER_SEP+'Fiscal Year'].get_value();        
     
  // make query based on transaction
  //-------------------------------------------------------------------------------------------

  var cond = '';  
  //for purchase order
  if(based_on == 'Purchase Order'){

    if(purchase_order) cond += ' AND `tabPurchase Order`.name = "'+purchase_order+'"';
    if(project_name) cond += ' AND `tabPurchase Order`.project_name = "'+project_name+'"';    
    if(company) cond += ' AND `tabPurchase Order`.company = "'+company+'"';
    if(fy !='') cond += ' AND `tabPurchase Order`.fiscal_year = "'+fy+'"'; 

    var q = 'SELECT DISTINCT `tabPurchase Order`.name, `tabPurchase Order`.status, `tabPurchase Order`.project_name, `tabPurchase Order`.supplier,`tabPurchase Order`.supplier_name,`tabPurchase Order`.per_received, `tabPurchase Order`.per_billed, `tabPurchase Order`.grand_total FROM `tabPurchase Order` WHERE IFNULL(`tabPurchase Order`.project_name,"") != ""'+cond+' AND `tabPurchase Order`.docstatus != 2';  
    return q;
  }  
  
  //for purchase receipt
  else if(based_on == 'Purchase Receipt'){
    if(purchase_order) cond += ' t2.purchase_order = "'+purchase_order+'" AND ';
    if(purchase_receipt) cond += ' t1.name = "'+purchase_receipt+'" AND ';
    if(project_name) cond += ' t1.project_name = "'+project_name+'" AND ';    
    if(company) cond += ' t1.company = "'+company+'" AND ';
    if(fy !='') cond += ' t1.fiscal_year = "'+fy+'" AND '; 
 
  
    var q = 'SELECT DISTINCT t1.name, t1.status, t1.project_name, t1.supplier, t1.supplier_name,t1.grand_total FROM `tabPurchase Receipt` t1,  `tabPurchase Receipt Detail` t2 WHERE '+cond +'IFNULL(t1.project_name,"") !="" AND t1.docstatus != 2 AND t1.name = t2.parent';
  
    return q;  
  }
  //for purchase invoice
  else if(based_on == 'Purchase Invoice'){
    if(purchase_order) cond += ' t2.purchase_order = "'+purchase_order+'" AND ';
    if(purchase_receipt) cond += ' t2.purchase_receipt = "'+purchase_receipt+'" AND';
    if(purchase_invoice) cond += ' t1.name = "'+purchase_invoice+'" AND';
    if(project_name) cond += ' t1.project_name = "'+project_name+'" AND ';    
    if(company) cond += ' t1.company = "'+company+'" AND ';
    if(fy !='') cond += ' t1.fiscal_year = "'+fy+'" AND ';     
    
    var q = 'SELECT DISTINCT t1.name , t1.credit_to , t1.project_name, t1.supplier, t1.supplier_name , t1.grand_total FROM `tabPayable Voucher` t1,  `tabPV Detail` t2 WHERE '+cond +'IFNULL(t1.project_name,"") !="" AND t1.docstatus != 2 AND t1.name = t2.parent';
  
    return q;  
  }  
}