## 15.3.1.8 ID der Ausgangsrechnung auf Grundlage der ID des Kundenauftrags

Das unten abgebildete Skript erlaubt es Ihnen die Benamungsserien der Ausgangsrechnungen und der zugehörigen Eingangsrechnungen gleich zu schalten. Die Ausgangsrechnung verwendet das Präfix M- aber die Nummer kopiert den Namen (die Nummer) des Kundenauftrags.

Beispiel: Wenn der Kundenauftrag die ID SO-12345 hat, dann bekommt die zugehörige Ausgangsrechnung die ID M-12345.

    frappe.ui.form.on("Sales Invoice", "refresh", function(frm){
        var sales_order = frm.doc.items[0].sales_order.replace("M", "M-");
        if (!frm.doc.__islocal && sales_order && frm.doc.name!==sales_order){
            frappe.call({
            method: 'frappe.model.rename_doc.rename_doc',
            args: {
                doctype: frm.doctype,
                old: frm.docname,
                "new": sales_order,
                "merge": false
           },
        });
        }
    });

{next}
