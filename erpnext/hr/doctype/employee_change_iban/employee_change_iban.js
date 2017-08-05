// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Change IBAN', {
	refresh: function(frm) {

	}
});
var englishCabitalAlphabet = /[A-Z]/i;
var numbersReg = /^\d+$/;
$('[data-fieldname="new_iban"]').on('keypress', english_cabital_numbers_only);
function english_cabital_numbers_only(e) {
  var key = String.fromCharCode(e.which);
  if (e.keyCode == 8 || e.keyCode == 32 || e.keyCode == 37 || e.keyCode == 39 || englishCabitalAlphabet.test(key) || numbersReg.test(key)) {
    return true;
  }
  return false;
}
