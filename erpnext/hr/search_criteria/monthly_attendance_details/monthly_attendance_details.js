var get_month = function(){

  var dict = {0:'Jan', 1:'Feb',2:'Mar',3:'Apr',4:'May',5:'June',6:'July',7:'Aug',8:'Sept',9:'Oct',10:'Nov',11:'Dec'}
  var d = new Date();
  return dict[d.getMonth()]

}

report.customize_filters = function() {
  this.hide_all_filters();
  this.add_filter({fieldname:'month', label:'Month', fieldtype:'Select', options:'Jan'+NEWLINE+'Feb'+NEWLINE+'Mar'+NEWLINE+'Apr'+NEWLINE+'May'+NEWLINE+'June'+NEWLINE+'July'+NEWLINE+'Aug'+NEWLINE+'Sept'+NEWLINE+'Oct'+NEWLINE+'Nov'+NEWLINE+'Dec',ignore : 1,parent:'Attendance', single_select:1});
  
  this.filter_fields_dict['Attendance'+FILTER_SEP +'Employee'].df.filter_hide = 0;
  this.filter_fields_dict['Attendance'+FILTER_SEP +'Month'].df.filter_hide = 0;
  this.filter_fields_dict['Attendance'+FILTER_SEP +'Fiscal Year'].df.filter_hide = 0;
  this.filter_fields_dict['Attendance'+FILTER_SEP +'Company'].df.filter_hide = 0;
  
  this.filter_fields_dict['Attendance'+FILTER_SEP +'Employee'].df.in_first_page = 1;
  this.filter_fields_dict['Attendance'+FILTER_SEP +'Month'].df.in_first_page = 1;
  this.filter_fields_dict['Attendance'+FILTER_SEP +'Fiscal Year'].df.in_first_page = 1;
  this.filter_fields_dict['Attendance'+FILTER_SEP +'Company'].df.in_first_page = 1;
  
  this.filter_fields_dict['Attendance'+FILTER_SEP +'Month'].df['report_default'] = get_month();
  this.filter_fields_dict['Attendance'+FILTER_SEP +'Company'].df['report_default'] = sys_defaults.company;
  this.filter_fields_dict['Attendance'+FILTER_SEP +'Fiscal Year'].df['report_default'] = sys_defaults.fiscal_year;
  this.get_filter('Attendance', 'Fiscal Year').set_as_single();
}
this.mytabs.items['More Filters'].hide();
this.mytabs.items['Select Columns'].hide();