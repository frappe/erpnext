# Kundenreklamationen
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Dass verkaufte Produkte zurück gesendet werden ist in der Wirtschaft üblich. Gründe für die Rücksendung durch den Kunden sind Qualitätsmängel, verspätete Lieferung oder auch anderes.

In ERPNext können Sie eine Kundenreklamation erstellen, indem Sie ganz einfach einen Lieferschein/eine Ausgangsrechnung mit negativer Menge erstellen.

Öffnen Sie dazu zuerst den Lieferschein/die Ausgangsrechnung zu dem/der der Kunde einen Artikel zurück sendet.

<img class="screenshot" alt="Original-Lieferschein" src="{{docs_base_url}}/assets/img/stock/sales-return-original-delivery-note.png">

Klicken Sie dann auf "Kundenreklamation erstellen", das öffnet einen neuen Lieferschein, bei dem "Ist Reklamation" aktiviert ist, und die Artikel und Steuern mit negativem Betrag angezeigt werden.
Sie können die Reklamation auch über die Originalausgangsrechnung erstellen. Um Material mit einer Gutschrift zurück zu geben, markieren Sie die Option "Lager aktualisieren" in der Reklamationsrechnung.

<img class="screenshot" alt="Kundenreklamation zum Lieferschein" src="{{docs_base_url}}/assets/img/stock/sales-return-against-delivery-note.png">		

Bei der Ausgabe eines Rücksendelieferscheins / einer Reklamationsrechnung erhöht das System den Lagerbestand im entsprechenden Lager. Um den richtigen Lagerwert zu erhalten erhöht sich der Lagerbestand um den Wert des ursprünglichen Einkaufspreises des zurückgeschickten Artikels.

<img class="screenshot" alt="Kundenreklamation zur Eingangsrechnung" src="{{docs_base_url}}/assets/img/stock/sales-return-against-sales-invoice.png">

Für den Fall einer Reklamationsrechnung erhält das Kundenkonto eine Gutschrift und die damit verknüpften Konten für Erträge und Steuern werden belastet.
Wenn die ständige Inventur aktiviert ist, erstellt das System auch Buchungen für das Lagerkonto um den Kontostand des Lagers mit dem Lagerbuch zu synchronisieren. 

<img class="screenshot" alt="Lagerbuch und Reklamation" src="{{docs_base_url}}/assets/img/stock/sales-return-stock-ledger.png">

<img class="screenshot" alt="Lagerbuch und Reklamation" src="{{docs_base_url}}/assets/img/stock/sales-return-general-ledger.png">

{next}
