
var doctype_data = [
    // Material Request
    {name:"Material Request", gregorian:"transaction_date", vikram_samvat: "date_nepal"},
    {name:"Material Request", gregorian:"schedule_date", vikram_samvat: "required_by_nepal"},
    // Purchase Order
    {name:"Purchase Order", gregorian:"transaction_date", vikram_samvat: "date_nepal"},
    {name:"Purchase Order", gregorian:"schedule_date", vikram_samvat: "required_by_nepal"},
    {name:"Purchase Order", gregorian:"from_date", vikram_samvat: "from_date_nepal"},
    {name:"Purchase Order", gregorian:"to_date", vikram_samvat: "to_date_nepal"},

    // Purchase Invoice
    {name:"Purchase Invoice", gregorian:"due_date", vikram_samvat: "due_date_nepal"},
    {name:"Purchase Invoice", gregorian:"posting_date", vikram_samvat: "date_nepal"},
    {name:"Purchase Invoice", gregorian:"to_date", vikram_samvat: "to_date_nepal"},
    {name:"Purchase Invoice", gregorian:"from_date", vikram_samvat: "from_date_nepal"},

    // Request for Quotation
    {name:"Request for Quotation", gregorian:"transaction_date", vikram_samvat: "date_nepal"},

    // Supplier Quotation
    {name:"Supplier Quotation", gregorian:"transaction_date", vikram_samvat: "date_nepal"},
    {name:"Supplier Quotation", gregorian:"valid_till", vikram_samvat: "valid_till_nepal"},

    // Item Price
    {name:"Item Price", gregorian:"valid_from", vikram_samvat: "valid_from_nepal"},
    {name:"Item Price", gregorian:"valid_upto", vikram_samvat: "valid_upto_nepal"},

    // Promotional Scheme
    {name:"Promotional Scheme", gregorian:"valid_from", vikram_samvat: "valid_from_nepal"},
    {name:"Promotional Scheme", gregorian:"valid_upto", vikram_samvat: "valid_upto_nepal"},

    // Pricing Rule
    {name:"Pricing Rule", gregorian:"valid_from", vikram_samvat: "valid_from_nepal"},
    {name:"Pricing Rule", gregorian:"valid_upto", vikram_samvat: "valid_upto_nepal"},

    // Sales Order
    {name:"Sales Order", gregorian:"transaction_date", vikram_samvat: "date_nepal"},
    {name:"Sales Order", gregorian:"delivery_date", vikram_samvat: "dalivery_date_nepal"},
    {name:"Sales Order", gregorian:"to_date", vikram_samvat: "to_date_nepal"},
    {name:"Sales Order", gregorian:"from_date", vikram_samvat: "from_date_nepal"},

    // Blanket Order
    {name:"Blanket Order", gregorian:"to_date", vikram_samvat: "to_date_nepal"},
    {name:"Blanket Order", gregorian:"from_date", vikram_samvat: "from_date_nepal"},

    // Coupon Code
    {name:"Coupon Code", gregorian:"valid_from", vikram_samvat: "valid_from_nepal"},
    {name:"Coupon Code", gregorian:"valid_upto", vikram_samvat: "valid_upto_nepal"},

    // Lead Details
    {name:"Lead Details", gregorian:"valid_from", vikram_samvat: "valid_from_nepal"},
    {name:"Lead Details", gregorian:"valid_upto", vikram_samvat: "valid_upto_nepal"},

    // Lead
    {name:"Lead", gregorian:"contact_date", vikram_samvat: "contact_date_nepal"},
    {name:"Lead", gregorian:"ends_on", vikram_samvat: "ends_on_nepal"},

    // Email Campaign
    {name:"Email Campaign", gregorian:"start_date", vikram_samvat: "start_date_nepal"},

    // Social Media Post
    {name:"Social Media Post", gregorian:"scheduled_time", vikram_samvat: "scheduled_time_nepal"},

    // Maintenance Schedule
    {name:"Maintenance Schedule", gregorian:"transaction_date", vikram_samvat: "date_nepal"},

    // Warranty Claim
    {name:"Warranty Claim", gregorian:"complaint_date", vikram_samvat: "issue_date_nepal"},
    {name:"Warranty Claim", gregorian:"warranty_expiry_date", vikram_samvat: "warranty_expire_date_nepal"},
    {name:"Warranty Claim", gregorian:"amc_expiry_date", vikram_samvat: "amc_expire_date_nepal"},
    {name:"Warranty Claim", gregorian:"resolution_date", vikram_samvat: "resolution_date_date_nepal"},

    // Salary Structure Assignment
    {name:"Salary Structure Assignment", gregorian:"from_date", vikram_samvat: "from_date_nepal"},

    // Payroll Entry
    {name:"Payroll Entry", gregorian:"posting_date", vikram_samvat: "posting_date_nepal"},
    {name:"Payroll Entry", gregorian:"start_date", vikram_samvat: "start_date_nepal"},
    {name:"Payroll Entry", gregorian:"end_date", vikram_samvat: "end_date_nepal"},

    // Salary Slip
    {name:"Salary Slip", gregorian:"posting_date", vikram_samvat: "posting_date_nepal"},
    {name:"Salary Slip", gregorian:"start_date", vikram_samvat: "start_date_nepal"},
    {name:"Salary Slip", gregorian:"end_date", vikram_samvat: "end_date_nepal"},

    // Payroll Period
    {name:"Payroll Period", gregorian:"start_date", vikram_samvat: "start_date_nepal"},
    {name:"Payroll Period", gregorian:"end_date", vikram_samvat: "end_date_nepal"},

    // Income Tax Slab
    {name:"Income Tax Slab", gregorian:"effective_from", vikram_samvat: "effective_from_nepal"},

    // // Fiscal Year
    // {name:"Fiscal Year", gregorian:"year_start_date", vikram_samvat: "year_start_date_nepal"},
    // {name:"Fiscal Year", gregorian:"year_end_date", vikram_samvat: "year_end_date_nepal"},
]

$(document).on('app_ready', function() {
    doctype_data.map(doctype => {
        frappe.ui.form.on(doctype.name, doctype.gregorian,            
             function(frm){
                frappe.call({
                    method:"erpnext.nepali_date.get_converted_date",
                    args: {
                        date: frm.doc[doctype['gregorian']]
                    },
                    callback: function(resp){
                        if(resp.message){
                            frm.set_value(doctype.vikram_samvat,resp.message)
                        }
                    }
                })
        })

        frappe.ui.form.on(doctype.name, "refresh",            
            function(frm){
               if(doctype.gregorian === "transaction_date" || doctype.gregorian === "posting_date"){
                frappe.call({
                    method:"erpnext.nepali_date.get_converted_date",
                    args: {
                        date: frm.doc[doctype['gregorian']]
                    },
                    callback: function(resp){
                        if(resp.message){
                            frm.set_value(doctype.vikram_samvat,resp.message)
                        }
                    }
                })
               }
       })

    })
    frappe.ui.form.on("Fiscal Year",{
        refresh: function(frm){
            frappe.db.get_single_value("System Settings", "country", (r) => {
                if(r.message){
                    if(r.message.country === "Nepal"){
                        frm.set_df_property("date_tablenepal", "hidden",0)
                    }
                }
            });
    },
})
})
