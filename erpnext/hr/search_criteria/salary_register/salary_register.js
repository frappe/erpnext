report.customize_filters = function() {
  fld_lst = ['ID','Employee']

  for(var i = 0; i<fld_lst.length; i++){
    this.filter_fields_dict['Salary Slip'+FILTER_SEP +fld_lst[i]].df.in_first_page = 1;
  }
  
}
this.mytabs.items['Select Columns'].hide();