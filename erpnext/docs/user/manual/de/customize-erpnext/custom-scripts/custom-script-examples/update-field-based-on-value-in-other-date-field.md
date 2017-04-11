# Datenfeld basierend auf dem Wert in einem anderen Datenfeld aktualisieren
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Das unten abgebildete Skript trägt automatisch einen Wert in das Feld Datum ein, das auf einem Wert in einem anderen Skript basiert.

Beispiel: Das Produktionsdatum muss sich zwei Tage vor dem Lieferdatum befinden. Wenn Sie das Feld zum Produktionsdatum haben, wobei es sich um ein Feld vom Typ Datum handelt, dann können Sie mit dem unten abgebildeten Skript das Datum in diesem Feld automatisch aktualisieren, zwei Tage vor dem Lieferdatum.

    cur_frm.cscript.custom_delivery_date = function(doc, cdt, cd){
    cur_frm.set_value("production_due_date", frappe.datetime.add_days(doc.delivery_date, -2));
     }

{next}
