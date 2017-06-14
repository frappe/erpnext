Add a handler to `custom_before_cancel` event:



    cur_frm.cscript.custom_before_cancel = function(doc) {
        if (frappe.user_roles.indexOf("Accounts User")!=-1 && frappe.user_roles.indexOf("Accounts Manager")==-1
                && user_roles.indexOf("System Manager")==-1) {
            if (flt(doc.grand_total) > 10000) {
                frappe.msgprint("You can not cancel this transaction, because grand total \
                    is greater than 10000");
                frappe.validated = false;
            }
        }
    }


{next}
