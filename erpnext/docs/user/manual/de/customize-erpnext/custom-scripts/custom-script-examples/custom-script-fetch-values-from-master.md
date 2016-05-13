# Benutzerdefiniertes Skript holt sich Werte aus der Formularvorlage
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Um einen Wert oder eine Verknüpfung auf eine Auswahl zu holen, verwenden Sie die Methode add_fetch.

> add_fetch(link_fieldname, source_fieldname, target_fieldname)

### Beispiel

Sie erstellen ein benutzerdefiniertes Feld **VAT ID** (vat_id) unter **Kunde** und **Ausgangsrechnung** und Sie möchten sicher stellen, dass dieser Wert immer aktualisiert wird, wenn Sie einen Kunden oder eine Ausgangsrechnung aufrufen.

Fügen Sie also im Skript Ausgangsrechnung Kunde Folgendes hinzu:

> cur_frm.add_fetch('customer','vat_id','vat_id')

* * *

Sehen Sie hierzu auch: [Wie man ein benutzerdefiniertes Skript erstellt]({{docs_base_url}}/user/manual/de/customize-erpnext/custom-scripts/).

{next}
