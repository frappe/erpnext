frappe.ui.form.on("Data Conversion", {
    refresh(frm) {
        if (frm.doc.missing_accounts && frm.doc.missing_accounts.trim() !== "") {
            frm.set_df_property("accounts_dictionary", "hidden", 0);
        } else {
            frm.set_df_property("accounts_dictionary", "hidden", 1);
        }

        if (frm.doc.missing_accounts) {
            frm.toggle_display('missing_accounts', true);
        } else {
            frm.toggle_display('missing_accounts', false);
        }

        // Toggle Missing Items section
        if (frm.doc.missing_items) {
            frm.toggle_display('missing_items', true);
        } else {
            frm.toggle_display('missing_items', false);
        }

        const hasMissing = frm.doc.missing_accounts || frm.doc.missing_items;
        const hasProcessedZip = frm.doc.processed_zip_file;
        frm.toggle_display('processed_zip_file', !hasMissing && !!hasProcessedZip);

        frm.fields_dict.download_converted_data.$input.off('click').on('click', () => {
            if (!frm.doc.name) {
                frappe.msgprint("Please save the document first.");
                return;
            }

            frappe.call({
                method: "erpnext.administration_dashboard.doctype.data_conversion.data_conversion.process_upload",
                args: { docname: frm.doc.name },
                callback: function (r) {
                    if (r.message && (r.message.missing_accounts || r.message.missing_items)) {
                        let missing_accounts = r.message.missing_accounts || "";
                        let missing_items = r.message.missing_items || "";

                        let msg = "";
                        if (missing_accounts) {
                            msg += `<b>Missing Accounts:</b><br>${missing_accounts.split(',').join('<br>')}<br><br>`;
                        }
                        if (missing_items) {
                            msg += `<b>Missing Items:</b><br>${missing_items.split(',').join('<br>')}`;
                        }
                        frappe.msgprint(msg);
                        frm.reload_doc();
                    }
                    else if (r.message && typeof r.message === 'string') {
                        // Success case: open file link
                        window.open(r.message, "_blank");
                        frm.reload_doc();
                    } 
                    else {
                        frappe.msgprint("Processing failed, Please recheck the file Uploaded");
                    }
                }
            });
        });
    }
});
