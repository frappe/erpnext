# Nach dem Speichern "Schreibschutz" einstellen
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Verwenden Sie die Methode cur_frm.set_df_property um die Anzeige Ihres Feldes zu aktualiseren.

In diesem Skript verwenden wir auch die Eigenschaft __islocal des Dokuments um zu prüfen ob das Dokument wenigstens einmal abgespeichert wurde oder nie. Wenn __islocal gleich 1 ist, dann wurde das Dokument noch nie gespeichert.

    frappe.ui.form.on("MyDocType", "refresh", function(frm) {
        // use the __islocal value of doc, to check if the doc is saved or not
        frm.set_df_property("myfield", "read_only", frm.doc.__islocal ? 0 : 1);
    }

{next}
