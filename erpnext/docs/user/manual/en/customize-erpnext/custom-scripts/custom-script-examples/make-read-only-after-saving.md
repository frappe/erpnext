# Make Read Only After Saving

Use the method `cur_frm.set_df_property` to update the field's display.

In this script we also use the `__islocal` property of the doc to check if the
document has been saved atleast once or is never saved. If `__islocal` is `1`,
then the document has never been saved.

    frappe.ui.form.on("MyDocType", "refresh", function(frm) {
        // use the __islocal value of doc, to check if the doc is saved or not
        frm.set_df_property("myfield", "read_only", frm.doc.__islocal ? 0 : 1);
    }

{next}
