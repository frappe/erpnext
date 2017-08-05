// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Medical Examination', {
	refresh: function(frm) {

	}
});

var dates_g = ['date'];

$.each(dates_g, function(index, element) {
  cur_frm.cscript['custom_' + element] = function(doc, cdt, cd) {
    cur_frm.set_value(element + '_hijri', doc[element]);
  };

  cur_frm.cscript['custom_' + element + '_hijri'] = function(doc, cdt, cd) {
    cur_frm.set_value(element, doc[element + '_hijri']);
  };

});
