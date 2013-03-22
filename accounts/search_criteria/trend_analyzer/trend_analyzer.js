// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

report.customize_filters = function() {
  this.hide_all_filters();
  this.dt.set_no_limit(1);

  // hide transaction based on permissions
  var all_transactions = ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice",
    "Purchase Order", "Purchase Receipt", "Purchase Invoice"];
  var transaction_list = [];
  $.each(all_transactions, function(i, dt) {
    if(wn.boot.profile.can_read.indexOf(dt)!=-1) {
      transaction_list.push(dt);
    }
  });
  
  this.add_filter({fieldname:'transaction', label:'Transaction', fieldtype:'Select', options:transaction_list.join(NEWLINE),report_default:'Delivery Note',ignore : 1,parent:'Profile',in_first_page : 1,single_select : 1});

  this.add_filter({fieldname:'period', label:'Period', fieldtype:'Select', options:'Monthly'+NEWLINE+'Quarterly'+NEWLINE+'Half Yearly'+NEWLINE+'Annual',report_default:'Quarterly',ignore : 1, parent:'Profile',in_first_page:1,single_select:1});

  this.add_filter({fieldname:'based_on', label:'Based On', fieldtype:'Select', options:'Item'+NEWLINE+'Item Group'+NEWLINE+'Customer'+NEWLINE+'Customer Group'+NEWLINE+'Territory'+NEWLINE+'Supplier'+NEWLINE+'Supplier Type'+NEWLINE+'Project', ignore : 1, parent:'Profile', report_default:'Item', in_first_page : 1,single_select:1});

  this.add_filter({fieldname:'group_by', label:'Group By', fieldtype:'Select', options:NEWLINE+'Item'+NEWLINE+'Customer'+NEWLINE+'Supplier', ignore : 1, parent:'Profile',single_select:1});

  this.add_filter({fieldname:'order_type', label:'Order Type', fieldtype:'Select', options:NEWLINE+'Sales'+NEWLINE+'Maintenance',ignore : 1, parent:'Profile',single_select:1});

  this.add_filter({fieldname:'company', label:'Company', fieldtype:'Link', options:'Company', report_default:sys_defaults.company, ignore : 1, parent:'Profile'});

  this.add_filter({fieldname:'fiscal_year', label:'Fiscal Year', fieldtype:'Link', options:'Fiscal Year', report_default:sys_defaults.fiscal_year, ignore : 1, parent:'Profile', in_first_page:1});


  // Add Filters
  this.add_filter({fieldname:'item', label:'Item', fieldtype:'Link', options:'Item', ignore : 1, parent:'Profile'});
  this.add_filter({fieldname:'item_group', label:'Item Group', fieldtype:'Link', options:'Item Group', ignore : 1, parent:'Profile'});
  this.add_filter({fieldname:'customer', label:'Customer', fieldtype:'Link', options:'Customer', ignore : 1, parent:'Profile'});
  this.add_filter({fieldname:'customer_group', label:'Customer Group', fieldtype:'Link', options:'Customer Group', ignore : 1, parent:'Profile'});
  this.add_filter({fieldname:'territory', label:'Territory', fieldtype:'Link', options:'Territory', ignore : 1, parent:'Profile'});
  this.add_filter({fieldname:'supplier', label:'Supplier', fieldtype:'Link', options:'Supplier', ignore : 1, parent:'Profile'});
  this.add_filter({fieldname:'supplier_type', label:'Supplier Type', fieldtype:'Link', options:'Supplier Type', ignore : 1, parent:'Profile'});
  this.add_filter({fieldname:'project', label:'Project', fieldtype:'Link', options:'Project', ignore : 1, parent:'Profile'});
}


this.mytabs.tabs['Select Columns'].hide();

report.aftertableprint = function(t) {
   $yt(t,'*',1,{whiteSpace:'pre'});
}

var validate_values = function(trans,based_on,order_type) {
  if(!fiscal_year){
    msgprint("Please select Fiscal Year");
    return 0;
  }
  if((in_list(['Quotation','Sales Order','Delivery Note','Sales Invoice'],trans) && in_list(['Supplier','Supplier Type'],based_on)) || (in_list(['Purchase Order','Purchase Receipt','Purchase Invoice'],trans) && in_list(['Customer','Customer Group','Territory'],based_on))){
    msgprint("Sorry! You cannot fetch "+trans+" trend based on "+based_on);
    return 0;
  }
  if(in_list(['Purchase Order','Purchase Receipt','Purchase Invoice'],trans) && order_type){
    msgprint("Please deselect Order Type for "+trans);
    return 0;
  }
  return 1;
}


report.get_query = function() {
  trans = this.get_filter('Profile', 'Transaction').get_value();
  order_type = this.get_filter('Profile', 'Order Type').get_value();
  based_on = this.get_filter('Profile', 'Based On').get_value();
  company = this.get_filter('Profile', 'Company').get_value();
  fiscal_year = this.get_filter('Profile', 'Fiscal Year').get_value();

  if(validate_values(trans,based_on,order_type)){
    col = '';
    add_cond = '';
    add_col = '';
    add_tables = '';
    sp_cond = '';

    trans_det = trans+' Item'

    if(order_type != '') add_code += ' AND t1.order_type = '+order_type;

    switch(based_on){
      case 'Item'           :     item = this.get_filter('Profile', 'Item').get_value();
                                  col = 'DISTINCT t2.item_code, t3.item_name';
                                  add_tables = ',tabItem t3';
                                  add_cond += ' AND t2.item_code = t3.name';
                                  if(item) add_cond += ' AND t2.item_code = "'+item+'"';
                                  break;
      case 'Customer'       :     cust = this.get_filter('Profile', 'Customer').get_value();
                                  col = 'DISTINCT t1.customer, t3.territory';
                                  add_tables = ',tabCustomer t3';
                                  add_cond += ' AND t1.customer = t3.name';
                                  if(cust) add_cond += ' AND t1.customer = "'+cust+'"';
                                  break;
      case 'Supplier'      :      supp = this.get_filter('Profile', 'Supplier').get_value();
                                  col = 'DISTINCT t1.supplier, t3.supplier_type';
                                  add_tables = ',tabSupplier t3';
                                  add_cond += ' AND t1.supplier = t3.name';
                                  if(supp) add_cond += ' AND t1.supplier = "'+supp+'"';
                                  break;
      case 'Supplier Type'  :     supp_type = this.get_filter('Profile', 'Supplier Type').get_value();
                                  col = 'DISTINCT t3.supplier_type';
                                  add_tables = ',tabSupplier t3';
                                  add_cond += ' AND t1.supplier = t3.name';
                                  if(supp_type) add_cond += ' AND t1.supplier_type = "'+supp_type+'"';
                                  break;
      case 'Project'        :     pro = this.get_filter('Profile', 'Project').get_value();
      							  if (inList(['Purchase Order', 'Purchase Receipt', 'Purchase Invoice'], trans)) {
									  col = 'DISTINCT t2.project_name';
    	                              if(pro) add_cond += ' AND t2.project_name = "'+pro+'"';
    	                          } else {
	    	                          col = 'DISTINCT t1.project_name';
    	                              if(pro) add_cond += ' AND t1.project_name = "'+pro+'"';
    	                          }
                                  break;
      case 'Item Group'     :     ig = this.get_filter('Profile', 'Item Group').get_value();
                                  if(ig) sp_cond += ' AND parent.name = "'+ig+'"';
                                  break;
      case 'Customer Group' :     cg = this.get_filter('Profile', 'Customer Group').get_value();
                                  if(cg) sp_cond += ' AND parent.name = "'+cg+'"';
                                  break;
      case 'Territory'      :     ter = this.get_filter('Profile', 'Territory').get_value();
                                  if(ter) sp_cond += ' AND parent.name = "'+ter+'"';
                                  break;

    }

    
    if(based_on == 'Item' || based_on == 'Customer' || based_on == 'Supplier' || based_on == 'Supplier Type' || based_on == 'Project')
      var q ='SELECT '+col+' FROM `tab'+trans+'` t1, `tab'+trans_det+'` t2 '+add_tables+' WHERE t1.fiscal_year = "'+fiscal_year+'" and t1.company = "'+company+'" and t2.parent = t1.name '+add_cond;
    else
      var q = 'SELECT CONCAT(REPEAT("     ", COUNT(parent.name) - 1), node.name) AS "Name" FROM `tab'+based_on+'` node,`tab'+based_on+'` parent WHERE node.lft BETWEEN parent.lft and parent.rgt and node.docstatus !=2 '+sp_cond+' GROUP BY node.name ORDER BY node.lft';
   
    return q;
  }
}
