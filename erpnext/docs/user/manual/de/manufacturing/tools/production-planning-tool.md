# Werkzeug zur Fertigungsplanung
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Das Werkzeug zur Fertigungsplanung unterstützt Sie dabei die Fertigung zu planen und Artikel für eine Periode einzukaufen (normalerweise eine Woche oder ein Monat).

Die Liste der Artikel kann über die offenen Kundenaufträge im System erstellt werden. Folgendes wird angelegt:

* Fertigungsaufträge für jeden Artikel.
* Materialanforderung für Artikel deren vorhergesagte Menge wahrscheinlich unter 0 fällt.

Um das Werkzeug zur Fertigungsplanung zu nutzen, gehen Sie zu:

> Fertigung > Werkzeuge > Werkzeug zur Fertigungsplanung

<img class="screenshot" alt="Werkzeug zur Fertigungsplanung" src="{{docs_base_url}}/assets/img/manufacturing/ppt.png">

### Schritt 1: Auswahl und Kundenauftrag

* Wählen Sie einen Kundenauftrag für die Materialanforderung über die Filterfunktion (Zeit, Artikel und Kunde) aus.
* Klicken Sie auf "Kundenaufträge aufrufen" um eine Übersicht zu erhalten.

<img class="screenshot" alt="Werkzeug zur Fertigungsplanung" src="{{docs_base_url}}/assets/img/manufacturing/ppt-get-sales-orders.png">

### Schritt 2: Artikel aus Kundenaufträgen abrufen

Sie können Artikel hinzufügen, entfernen oder die Menge dieser Artikel verändern.

<img class="screenshot" alt="Werkzeug zur Fertigungsplanung" src="{{docs_base_url}}/assets/img/manufacturing/ppt-get-item.png">

### Schritt 3: Fertigungsaufträge erstellen

<img class="screenshot" alt="Werkzeug zur Fertigungsplanung" src="{{docs_base_url}}/assets/img/manufacturing/ppt-create-production-order.png">

### Schritt 4: Materialanfragen erstellen

Erstellen Sie für Artikel mit prognostiziertem Engpass Materialanfragen.

<img class="screenshot" alt="Werkzeug zur Fertigungsplanung" src="{{docs_base_url}}/assets/img/manufacturing/ppt-create-material-request.png">

Das Werkzeug zur Fertigungsplanung wird auf zwei Ebenend verwendet:

* Auswahl von offenen Kundenaufträge einer Periode auf Basis des erwarteten Lieferdatums.
* Auswahl von Artikeln aus diesen Kundenaufträgen.

Das Werkzeug erstellt eine Aktualisierung, wenn Sie bereits einen Kundenauftrag für einen bestimmten Artikel zu einem Kundenauftrag erstellt haben ("geplante Menge").

Sie könnenjederzeit die Artikelliste bearbeiten und die zur Fertigung geplante Menge erhöhen bzw. vermindern.

> Anmerkung: Wie ändern Sie einen Fertigungsplan? Des Ergebnis des Werkzeuges zur Produktionsplanung ist der Fertigungsauftrag. Sobald Ihre Aufträge erstellt wurden, können Sie sie ändern, indem Sie die Fertigungsaufträge ändern.

{next}
