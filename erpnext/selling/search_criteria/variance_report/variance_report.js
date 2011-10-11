report.customize_filters = function() {
  this.hide_all_filters();
  this.add_filter({fieldname:'based_on', label:'Based On', fieldtype:'Select', options:'Territory'+NEWLINE+'Sales Person'+NEWLINE+'Sales Partner',report_default:'Territory',ignore : 1,parent:'Target Detail'});
  this.add_filter({fieldname:'fiscal_year', label:'Fiscal Year', fieldtype:'Link', options:'Fiscal Year', report_default:sys_defaults.fiscal_year, ignore : 1, parent:'Target Detail'});
  this.add_filter({fieldname:'company', label:'Company', fieldtype:'Link', options:'Company',report_default:sys_defaults.company, ignore : 1, parent:'Target Detail'});
  this.add_filter({fieldname:'period', label:'Period', fieldtype:'Select', options:'Monthly'+NEWLINE+'Quarterly'+NEWLINE+'Half Yearly'+NEWLINE+'Annual',report_default:'Quarterly',ignore : 1, parent:'Target Detail'});
//  this.add_filter({fieldname:'item_group', label:'Item Group', fieldtype:'Link', options:'Item Group', ignore : 1, parent:'Target Detail'});
  this.add_filter({fieldname:'group_by', label:'Group By', fieldtype:'Select', options:NEWLINE+'Item Group',ignore : 1, parent:'Target Detail'});
  this.add_filter({fieldname:'under', label:'Under',fieldtype:'Select', options:'Sales Order'+NEWLINE+'Delivery Note'+NEWLINE+'Receivable Voucher',report_default:'Sales Order',ignore : 1, parent:'Target Detail'});
}  

//this.mytabs.items['Select Columns'].hide()
