report.customize_filters = function() {
  this.add_filter({fieldname:'based_on', label:'Based On', fieldtype:'Select', options:'Sales Order'+NEWLINE+'Delivery Note'+NEWLINE+'Receivable Voucher',report_default:'Sales Order',ignore : 1, parent:'Territory'});
  this.add_filter({fieldname:'fiscal_year', label:'Fiscal Year', fieldtype:'Link', options:'Fiscal Year', report_default:sys_defaults.fiscal_year, ignore : 1, parent:'Territory'});
  this.add_filter({fieldname:'company', label:'Company', fieldtype:'Link', options:'Company',report_default:sys_defaults.company, ignore : 1, parent:'Territory'});
  this.add_filter({fieldname:'period', label:'Period', fieldtype:'Select', options:'Monthly'+NEWLINE+'Quarterly'+NEWLINE+'Half Yearly'+NEWLINE+'Annual',report_default:'Quarterly',ignore : 1, parent:'Territory'});
}