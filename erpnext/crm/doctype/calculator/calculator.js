// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

//frappe.ui.form.on('Calculator',
 //{
	// refresh: function(frm) {

	// }

	//frappe.ui.form.on("Calculator", "first_number", function(frm) 
	
	  // {
		//frm.set_value("result", flt(frm.doc.first_number) + flt(frm.doc.second_number));
	  // })	  
	 // frappe.ui.form.on("Calculator", "second_number", function(frm)
	  // {
		//frm.set_value("result", flt(frm.doc.first_number) + flt(frm.doc.second_number));
	  //})

// });



// if (frm.doc.operator == "+")
	// {
	// 	frm.set_value("result", flt(frm.doc.first_number) + flt(frm.doc.second_number));	
	
	// }	
	// else
	// {	
	// alert('hi')
	// }

frappe.ui.form.on("Calculator",
{
	first_number: function(frm)
	{
		calculate(frm);
	},
	second_number: function(frm)
	{
		calculate(frm);
	},
	operator: function(frm)
	{
		calculate(frm);
	}
	
});
function calculate(frm)
{
	if (frm.doc.operator === "+")
	{
		frm.set_value("result", flt(frm.doc.first_number) + flt(frm.doc.second_number));
	}
	else if (frm.doc.operator === "-")
	{
		frm.set_value("result", flt(frm.doc.first_number) - flt(frm.doc.second_number));
	}
	else if (frm.doc.operator === "*")
	{
		frm.set_value("result", flt(frm.doc.first_number) * flt(frm.doc.second_number));
	}
	else if (frm.doc.operator === "/")
	{
		frm.set_value("result", flt(frm.doc.first_number) / flt(frm.doc.second_number));
	}
}

