report.customize_filters = function() {
  //hide all filters
  //------------------------------------------------
  this.hide_all_filters();

  //add filters
  //------------------------------------------------
  this.add_filter({fieldname:'based_on', label:'Based On', fieldtype:'Select', options:'Sales Order'+NEWLINE+'Delivery Note'+NEWLINE+'Sales Invoice',report_default:'Sales Order',ignore : 1,parent:'Sales Order', single_select:1});

  this.add_filter({fieldname:'sales_order', label:'Sales Order', fieldtype:'Link', options:'Sales Order', ignore : 1, parent:'Sales Order'});
  this.add_filter({fieldname:'delivery_note', label:'Delivery Note', fieldtype:'Link', options:'Delivery Note',ignore : 1, parent:'Sales Order'});
  this.add_filter({fieldname:'sales_invoice', label:'Sales Invoice',fieldtype:'Link', options:'Sales Invoice',ignore : 1, parent:'Sales Order'});

  //unhide filters
  //------------------------------------------------  
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Project Name'].df.filter_hide = 0;
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Company'].df.filter_hide = 0;
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Fiscal Year'].df.filter_hide = 0;  
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Customer'].df.filter_hide = 0;

  //move filter field in first page
  //------------------------------------------------  
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Based On'].df.in_first_page = 1;
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Project Name'].df.in_first_page = 1;
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Sales Order'].df.in_first_page = 1;
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Delivery Note'].df.in_first_page = 1;
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Sales Invoice'].df.in_first_page = 1;   

  // default values
  //------------------------------------------------  
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Company'].df['report_default'] = sys_defaults.company;
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Fiscal Year'].df['report_default'] = sys_defaults.fiscal_year;

}

//hide select columns field
//------------------------------------------------
//this.mytabs.items['Select Columns'].hide();


report.get_query = function() {

  //get filter values
  based_on = this.filter_fields_dict['Sales Order'+FILTER_SEP+'Based On'].get_value();   
  sales_order = this.filter_fields_dict['Sales Order'+FILTER_SEP+'Sales Order'].get_value();
  delivery_note = this.filter_fields_dict['Sales Order'+FILTER_SEP+'Delivery Note'].get_value();
  sales_invoice = this.filter_fields_dict['Sales Order'+FILTER_SEP+'Sales Invoice'].get_value();      
  project_name = this.filter_fields_dict['Sales Order'+FILTER_SEP+'Project Name'].get_value();      
  company = this.filter_fields_dict['Sales Order'+FILTER_SEP+'Company'].get_value();      
  fy = this.filter_fields_dict['Sales Order'+FILTER_SEP+'Fiscal Year'].get_value();      

  // make query based on transaction
  //-------------------------------------------------------------------------------------------

  var cond = '';  
  //for sales order
  if(based_on == 'Sales Order'){

    if(sales_order) cond += ' AND `tabSales Order`.name = "'+sales_order+'"';
    if(project_name) cond += ' AND `tabSales Order`.project_name = "'+project_name+'"';    
    if(company) cond += ' AND `tabSales Order`.company = "'+company+'"';
    if(fy) cond += ' AND `tabSales Order`.fiscal_year = "'+fy+'"'; 
           
    var q = 'SELECT DISTINCT `tabSales Order`.name, `tabSales Order`.order_type, `tabSales Order`.status, `tabSales Order`.project_name, `tabSales Order`.customer,`tabSales Order`.customer_name,`tabSales Order`.per_delivered, `tabSales Order`.per_billed, `tabSales Order`.grand_total FROM `tabSales Order` WHERE IFNULL(`tabSales Order`.project_name,"") != ""'+cond+' AND `tabSales Order`.docstatus != 2';  
    return q;
  }  
  
  //for delivery note
  else if(based_on == 'Delivery Note'){
    if(sales_order) cond += ' t1.name = t2.parent AND t2.prevdoc_docname = "'+sales_order+'" AND ';
    if(delivery_note) cond += ' t1.name = "'+delivery_note+'" AND ';
    if(project_name) cond += ' t1.project_name = "'+project_name+'" AND ';    
    if(company) cond += ' t1.company = "'+company+'" AND ';
    if(fy) cond += ' t1.fiscal_year = "'+fy+'" AND '; 
    
    var q = 'SELECT DISTINCT t1.name, t1.status, t1.project_name, t1.customer, t1.customer_name, t1.per_billed, t1.per_installed, t1.grand_total FROM `tabDelivery Note` t1, `tabDelivery Note Detail` t2  WHERE '+cond+' IFNULL(t1.project_name,"") !="" AND t1.docstatus != 2';

    return q;
  }
  
  //for sales invoice
  else if(based_on == 'Sales Invoice'){
    if(sales_order) cond += ' t2.sales_order = "'+sales_order+'" AND ';
    if(delivery_note) cond += ' t2.delivery_note = "'+delivery_note+'" AND ';
    if(sales_invoice) cond += ' t1.name = "'+sales_invoice+'" AND ';
    if(project_name) cond += ' t1.project_name = "'+project_name+'" AND '; 
    if(company) cond += ' t1.company = "'+company+'" AND ';
    if(fy) cond += ' t1.fiscal_year = "'+fy+'" AND '; 

       
    var q = 'SELECT DISTINCT t1.name , t1.debit_to , t1.project_name , t1.customer , t1.customer_name , t1.grand_total  FROM `tabReceivable Voucher` t1,  `tabRV Detail` t2 WHERE '+cond +'IFNULL(t1.project_name,"") !="" AND t1.docstatus != 2 AND t1.name = t2.parent';

    return q;  
  }
  
}