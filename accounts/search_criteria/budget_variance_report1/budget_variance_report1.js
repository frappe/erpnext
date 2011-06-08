report.customize_filters = function() {
  this.hide_all_filters();
  this.add_filter({fieldname:'fiscal_year', label:'Fiscal Year', fieldtype:'Link', options:'Fiscal Year', report_default:sys_defaults.fiscal_year, parent:'Budget Detail'});
  this.add_filter({fieldname:'company', label:'Company', fieldtype:'Link', options:'Company',report_default:sys_defaults.company, ignore : 1, parent:'Budget Detail'});
  this.add_filter({fieldname:'period', label:'Period', fieldtype:'Select', options:'Monthly'+NEWLINE+'Quarterly'+NEWLINE+'Half Yearly'+NEWLINE+'Annual',report_default:'Quarterly',ignore : 1, parent:'Budget Detail'});
  this.add_filter({fieldname:'cost_center', label:'Cost Center', fieldtype:'Link', options:'Cost Center', parent:'Budget Detail'});
  this.add_filter({fieldname:'account_head', label:'Account', fieldtype:'Link', options:'Account', parent:'Budget Detail'});
}
this.mytabs.items['Select Columns'].hide()