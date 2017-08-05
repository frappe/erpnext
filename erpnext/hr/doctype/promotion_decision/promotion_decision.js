// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch('employee', 'grade', 'grade');
cur_frm.add_fetch('employee', 'employee_name', 'employee_name');
// cur_frm.add_fetch('employee', 'region', 'region');
cur_frm.add_fetch('employee', 'branch', 'branch');
cur_frm.add_fetch('employee', 'department', 'department');
cur_frm.add_fetch('employee', 'designation', 'designation');
cur_frm.add_fetch('employee', 'employment_type', 'employment_type');
cur_frm.add_fetch('employee', 'civil_id', 'civil_id');
cur_frm.add_fetch('employee', 'date_of_joining', 'date_of_joining');
// cur_frm.add_fetch('employee', 'nationality', 'nationality');
// cur_frm.add_fetch('employee', 'gender', 'gender');

cur_frm.add_fetch('job_opening', 'grade', 'new_grade');
cur_frm.add_fetch('job_opening', 'branch', 'new_branch');
cur_frm.add_fetch('job_opening', 'department', 'new_department');
cur_frm.add_fetch('job_opening', 'designation', 'new_designation');
cur_frm.add_fetch('job_opening', 'employment_type', 'new_employment_type');

cur_frm.add_fetch('employee', 'grade', 'new_grade');
cur_frm.add_fetch('employee', 'employee_name', 'new_employee_name');
// cur_frm.add_fetch('employee', 'region', 'new_region');
cur_frm.add_fetch('employee', 'branch', 'new_branch');
cur_frm.add_fetch('employee', 'department', 'new_department');
cur_frm.add_fetch('employee', 'designation', 'new_designation');
cur_frm.add_fetch('employee', 'employment_type', 'new_employment_type');

cur_frm.add_fetch('new_grade', 'main_payment', 'main_payment');
// cur_frm.add_fetch('new_grade', 'total_earning', 'total_earning');
// cur_frm.add_fetch('new_grade', 'total_deduction', 'total_deduction');
// cur_frm.add_fetch('new_grade', 'net_pay', 'net_pay');
// cur_frm.add_fetch('new_grade', 'accommodation_from_company', 'accommodation_from_company');
// cur_frm.add_fetch('new_grade', 'accomodation_percentage', 'accomodation_percentage');
// cur_frm.add_fetch('new_grade', 'accommodation_value', 'accommodation_value');
// cur_frm.add_fetch('new_grade', 'transportation_costs', 'transportation_costs');



frappe.ui.form.on('Promotion Decision', {
  refresh: function(frm) {
		// cur_frm.set_df_property("accomodation_percentage", "read_only", frm.doc.accommodation_from_company);
		// cur_frm.set_df_property("accommodation_value", "read_only", frm.doc.accommodation_from_company);
	}
});
// cur_frm.cscript.custom_new_grade = function(doc, cdt, cd) {
//   // cur_frm.clear_table("earnings");
//   // cur_frm.clear_table("deductions");
//   // frappe.call({
//   //   doc: doc,
//   //   method: "get_child_table",
//   //   callback: function(r) {
//   //     console.log(r.message);
//   //     cur_frm.refresh_fields(["deductions", "earnings", "main_payment", "total_earning", "total_deduction", "net_pay",
// 		// "accommodation_from_company","accomodation_percentage","accommodation_value","transportation_costs"]);
//   //   }
//   // });
// };
// cur_frm.fields_dict.job_opening.get_query = function(doc) {
//   return {
//     filters: [
//       ['status', '=', "Open"]
//     ]
//   };
// };
cur_frm.fields_dict.employee.get_query = function(doc) {
  return {
    filters: [
      ['status', '=', "Active"]
    ]
  };
};
// var dates_g = ['decision_date', 'due_date', 'commencement_date'];

// $.each(dates_g, function(index, element) {
//   cur_frm.cscript['custom_' + element] = function(doc, cdt, cd) {
//     cur_frm.set_value(element + '_hijri', doc[element]);
//   };
//   cur_frm.cscript['custom_' + element + '_hijri'] = function(doc, cdt, cd) {
//     cur_frm.set_value(element, doc[element + '_hijri']);
//   };
// });



// cur_frm.fields_dict.job_opening.get_query = function(doc) {
//   return {
//     filters: {
//       status: "Open"
//     }
//   };
// };

// cur_frm.cscript.modified_value = function(doc, cdt, cdn) {
//   calculate_totals(doc, cdt, cdn);
// };

///////////////////////////////

// cur_frm.cscript.modified_value = function(doc, cdt, cdn) {
//   calculate_totals(doc, cdt, cdn);
// };

// cur_frm.cscript.d_modified_amt = function(doc, cdt, cdn) {
//   calculate_totals(doc, cdt, cdn);
// };

// var calculate_totals = function(doc, cdt, cdn) {
//   var tbl1 = doc.earnings || [];
//   var tbl2 = doc.deductions || [];

//   var total_earn = 0;
//   var total_ded = 0;
//   for (var i = 0; i < tbl1.length; i++) {
//     total_earn += flt(tbl1[i].modified_value);
//   }
//   for (var j = 0; j < tbl2.length; j++) {
//     total_ded += flt(tbl2[j].d_modified_amt);
//   }
//   if (doc.main_payment) {

//     doc.total_earning = total_earn + flt(doc.main_payment) + flt(doc.accommodation_value)+flt(doc.transportation_costs);
//     doc.total_deduction = total_ded;
//     doc.net_pay = flt(total_earn) + flt(doc.main_payment) - flt(total_ded) + flt(doc.accommodation_value)+flt(doc.transportation_costs);

//   } else {
//     console.log("Enter Main Earning");
//   }
//   refresh_many(['total_earning', 'total_deduction', 'net_pay']);
// };

cur_frm.cscript.validate = function(doc, cdt, cdn) {
  // calculate_totals(doc, cdt, cdn);
  if (doc.employee && doc.is_active == "Yes") frappe.model.clear_doc("Employee", doc.employee);
};


// cur_frm.cscript.custom_modified_value = function(doc, cdt, cd, cdn) {
//   //var percant_temp = cur_frm.fields_dict.earnings.grid.open_grid_row.get_open_form();
//   var temp = frappe.ui.form.get_open_grid_form();
//   if (doc.main_payment || Math.round(doc.main_payment) > 0) {
//     if (flt(temp.doc.modified_value) < 0) {
//       temp.doc.modified_value = 0;
//       refresh_many(['earnings', 'deductions']);
//       calculate_totals(doc, cdt, cdn);
//       alert("Can not add Negative value");
//     } else {
//       temp.doc.e_percentage = 100 * (temp.doc.modified_value / doc.main_payment);
//       calculate_totals(doc, cdt, cdn);
//       refresh_many(['earnings', 'deductions', 'total_earning']);
//     }
//   } else {
//     console.log("Enter Main Earning");
//   }
// };
// cur_frm.cscript.custom_e_percentage = function(doc, cdt, cd, cdn) {
//   var temp = frappe.ui.form.get_open_grid_form();
//   if (doc.main_payment || Math.round(doc.main_payment) > 0) {
//     if (flt(temp.doc.e_percentage) < 0) {
//       temp.doc.e_percentage = 0;
//       refresh_many(['earnings', 'deductions']);
//       calculate_totals(doc, cdt, cdn);
//       alert("Can not add Negative value");
//     } else {
//       temp.doc.modified_value = (doc.main_payment * temp.doc.e_percentage) / 100;
//       calculate_totals(doc, cdt, cdn);
//       refresh_many(['earnings', 'deductions', 'total_earning']);
//     }
//   } else {
//     console.log("Enter Main Earning");
//   }

// };
// cur_frm.cscript.custom_d_modified_amt = function(doc, cdt,cd, cdn) {

//   var temp = frappe.ui.form.get_open_grid_form();
//   if (doc.main_payment || Math.round(doc.main_payment) > 0) {
//     if (flt(temp.doc.d_modified_amt) < 0) {
//       temp.doc.d_modified_amt = 0;
//       refresh_many(['earnings', 'deductions']);
//       calculate_totals(doc, cdt, cdn);
//       alert("Can not add Negative value");
//     } else {
//       calculate_totals(doc, cdt, cdn);
//       if (temp.doc.based_on_total === 1) {
//         temp.doc.d_percentage = 100 * (temp.doc.d_modified_amt / doc.total_earning);
//       } else {
//         temp.doc.d_percentage = 100 * (temp.doc.d_modified_amt / doc.main_payment);
//       }
//       calculate_totals(doc, cdt, cdn);
//       refresh_many(['earnings', 'deductions']);
//     }
//   } else {
//     console.log("Enter Main Earning");
//   }

// };
// cur_frm.cscript.custom_d_percentage = function(doc, cdt, cd, cdn) {
//   var temp = frappe.ui.form.get_open_grid_form();
//   if (doc.main_payment || Math.round(doc.main_payment) > 0) {
//     if (flt(temp.doc.d_percentage) < 0) {
//       temp.doc.d_percentagee = 0;
//       refresh_many(['earnings', 'deductions']);
//       calculate_totals(doc, cdt, cdn);
//       alert("Can not add Negative value");
//     } else {
//       calculate_totals(doc, cdt, cdn);
//       if (temp.doc.based_on_total === 1)
//         temp.doc.d_modified_amt = (doc.total_earning * temp.doc.d_percentage) / 100;
//       else {
//         temp.doc.d_modified_amt = (doc.main_payment * temp.doc.d_percentage) / 100;
//       }
//       calculate_totals(doc, cdt, cdn);
//       refresh_many(['earnings', 'deductions', 'total_earning']);
//     }
//   } else {
//     console.log("Enter Main Earning");
//   }

// };
// cur_frm.cscript.custom_transportation_costs=cur_frm.cscript.custom_main_payment = function(doc, cdt, cd, cdn) {
// 	// calculate_totals(doc, cdt, cdn);
// };
// cur_frm.cscript.custom_accomodation_percentage = function(doc, cdt, cd, cdn) {
//   if (doc.main_payment || Math.round(doc.main_payment) > 0) {
//     if (flt(doc.accomodation_percentage) < 0) {
//       doc.accomodation_percentage = 0.00;
//       doc.accommodation_value = 0.00;
//       refresh_many(['accomodation_percentage', 'accommodation_value']);
//       calculate_totals(doc, cdt, cdn);
//       alert("Accomodation Percentage can not be Negative");
//     } else {
//       doc.accommodation_value = (doc.main_payment * doc.accomodation_percentage) / 100;
//       calculate_totals(doc, cdt, cdn);
//       refresh_many(['accomodation_percentage', 'accommodation_value']);
//     }
//   } else {
// 		doc.accomodation_percentage = 0.00;
// 		doc.accommodation_value = 0.00;
// 		refresh_many(['accomodation_percentage', 'accommodation_value']);
//     console.log("Enter Main Earning");
//   }

// };
// cur_frm.cscript.custom_accommodation_value = function(doc, cdt, cd, cdn) {
//   if (doc.main_payment || Math.round(doc.main_payment) > 0) {
//     if (flt(doc.accommodation_value) < 0) {
//       doc.accomodation_percentage = 0.00;
//       doc.accommodation_value = 0.00;
//       refresh_many(['accomodation_percentage', 'accommodation_value']);
//       calculate_totals(doc, cdt, cdn);
//       alert("Accomodation Value can not be Negative");
//     } else {
//       doc.accomodation_percentage = 100 * (doc.accommodation_value / doc.main_payment);
//       calculate_totals(doc, cdt, cdn);
//       refresh_many(['accomodation_percentage', 'accommodation_value']);
//     }
//   } else {
// 		doc.accomodation_percentage = 0.00;
// 		doc.accommodation_value = 0.00;
// 		refresh_many(['accomodation_percentage', 'accommodation_value']);
//   }

// };
// frm.set_df_property("myfield", "read_only", frm.doc.__islocal ? 0 : 1);
// cur_frm.cscript.custom_accommodation_from_company = function(doc, cdt, cd, cdn) {
//   if (doc.accommodation_from_company === 1) {
//     doc.accomodation_percentage = 0.00;
//     doc.accommodation_value = 0.00;
//     refresh_many(['accomodation_percentage', 'accommodation_value']);
//     calculate_totals(doc, cdt, cdn);
//   }
//   cur_frm.set_df_property("accomodation_percentage", "read_only", doc.accommodation_from_company);
//   cur_frm.set_df_property("accommodation_value", "read_only", doc.accommodation_from_company);
//   refresh_many(['accomodation_percentage', 'accommodation_value']);
// };
// cur_frm.add_fetch('employee', 'company', 'company');
// cur_frm.cscript.custom_grade = function(doc, cdt, cd, cdn) {
//   return frappe.call({
//     type: "GET",
//     method: "erpnext.hr.doctype.salary_structure.salary_structure.get_grade",
//     args: {
//       grade_name: doc.grade
//     },
//     callback: function(r) {
//       if (!r.exc && r.message) {
//         console.log(r.message.earnings);
//         cur_frm.clear_table("earnings");
//         refresh_many(['earnings']);
//         if (r.message.earnings) {
//           $.each(r.message.earnings, function(i, d) {
//             var row = frappe.model.add_child(cur_frm.doc, "Salary Structure Earning", "earnings");
//             row.e_type = d.e_type;
//             row.modified_value = d.modified_value;
//             row.e_percentage = d.e_percentage;
//             row.depend_on_lwp = d.depend_on_lwp;
//             refresh_field("earnings");
//             calculate_totals(doc, cdt, cdn);
//           });
//         }

//       }
//     }

//   });
// };
