// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Grade', {
  refresh: function(frm) {

  }
});
$('[data-fieldname="main_earning"]').on('keypress', numbersonly);
$('[data-fieldname="accommodation"]').on('keypress', numbersonly);


function numbersonly(e) {
  var unicode = e.charCode ? e.charCode : e.keyCode;
  if (unicode != 8) { //if the key isn't the backspace key (which we should allow)
    if (unicode < 48 || unicode > 57) //if not a number
      return false; //disable key press
  }
}

cur_frm.add_fetch('employee', 'company', 'company');
cur_frm.add_fetch('employee', 'grade', 'grade');
cur_frm.add_fetch('grade', 'insurance', 'insurance');

cur_frm.cscript.onload = function(doc, dt, dn) {
  if ((cint(doc.__islocal) !== 1)) {
    cur_frm.set_df_property("accomodation_percentage", "read_only", doc.accommodation_from_company);
    cur_frm.set_df_property("accommodation_value", "read_only", doc.accommodation_from_company);
  }
};

cur_frm.cscript.refresh = function(doc, dt, dn) {

};


cur_frm.cscript.employee = function(doc, dt, dn) {

};
