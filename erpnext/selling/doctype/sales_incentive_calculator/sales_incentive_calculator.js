// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sales Incentive Calculator', {
	get_invoice:function(frm,cdt,cdn){
        frappe.call({
        method:"nextsales.customer_incentive.doctype.sales_incentive_calculator.sales_incentive_calculator.fetch_details",
        args:{
                "fd":frm.doc.from_date,
                "td":frm.doc.to_date
        },
        callback: function(r) {
            $.each(r.message,function(index,row)
            {
                var child=frm.add_child("invoice_list")
                child.sales_invoice=row.name,
                child.customer=row.customer,
                child.amount=row.outstanding_amount,
                child.date=row.posting_date
            });frm.refresh_field('invoice_list');

        }
    });

  },
  get_payment:function(frm,cdt,cdn){
        frappe.call({
        method:"nextsales.customer_incentive.doctype.sales_incentive_calculator.sales_incentive_calculator.get_payment",
        args:{
                "fd":frm.doc.from_date,
                "td":frm.doc.to_date
        },
        callback: function(r) {
        console.log(r.message)
            $.each(r.message,function(index,row)
            {
                console.log(index)
                console.log(row)
                var child=frm.add_child("payment_list")
                child.payment_id=row.name,
                child.customer=row.party_name,
                child.amount=row.total_allocated_amount,
                child.date=row.posting_date
            }

            );frm.refresh_field('payment_list');

        }
    });

  }

});