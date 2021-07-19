// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sales Incentive Calculator', {
	get_invoice:function(frm,cdt,cdn){
        frappe.call({
        method:"erpnext.selling.doctype.sales_incentive_calculator.sales_incentive_calculator.fetch_details",
        args:{
            "customer_sales_incentive":frm.doc.customer_sales_incentive    
        },
        callback: function(r) {
            frm.clear_table('invoice_list');
            $.each(r.message,function(index,row)
            {
                var child=frm.add_child("invoice_list")
                child.sales_invoice=row.name,
                child.customer=row.customer,
                child.amount=row.amount,
                child.date=row.posting_date,
                child.item=row.item_code,
                child.item_name=row.item_name,
                child.rate=row.rate,
                child.customer_name=row.customer_name,
                child.qty=row.qty
            });frm.refresh_field('invoice_list');
            frm.set_df_property('get_invoice', 'hidden', 1);
        }
    });

  },
  get_payment:function(frm,cdt,cdn){
        frappe.call({
        method:"erpnext.selling.doctype.sales_incentive_calculator.sales_incentive_calculator.get_payment",
        args:{
            "customer_sales_incentive":frm.doc.customer_sales_incentive
            
        },
        callback: function(r) {
            frm.clear_table('invoice_list');
            $.each(r.message,function(index,row)
            {
                var child=frm.add_child("invoice_list")
                child.sales_invoice=row.name,
                child.customer=row.customer,
                child.amount=row.amount,
                child.date=row.posting_date,
                child.item=row.item_code,
                child.item_name=row.item_name,
                child.qty=row.qty,
                child.rate=row.rate,
                child.customer_name=row.customer_name
            });frm.refresh_field('invoice_list');
            frm.set_df_property('get_payment', 'hidden', 1);
        }
        
    });

  },
  onload:function(frm){
    frm.call({
            method: "erpnext.selling.doctype.sales_incentive_calculator.sales_incentive_calculator.get_list",
            callback: function(r) {
                console.log(r.message)
                if (r.message) {
                    frm.set_query("customer_sales_incentive", function() {
                        return {
                            filters: [
                                ["name", "in", r.message]
                            ]
                        }
                    });
                }
            }

    });
},


});