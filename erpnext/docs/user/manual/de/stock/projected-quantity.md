# Projizierte Menge
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Die projizierte Menge ist der Lagerbestand der für einen bestimmten Artikel vorhergesagt wird, basierend auf dem aktuellen Lagerbestand und anderen Bedarfen. Es handelt sich dabei um den Bruttobestand und berücksichtig Angebot und Nachfrage aus der Vergangenheit, die mit in den Planungsprozess einbezogen werden.

Der projizierte Lagerbestand wird vom Planungssystem verwendet um den Nachbestellpunkt darzustellen und die Nachbestellmenge festzulegen. Die projizierte Menge wird vom Planungssystem verwendet um Sicherheitsbestände zu markieren. Diese Stände werden aufrechterhalten um unerwartete Nachfragemengen abfedern zu können.

Eine strikte Kontrolle des projizierten Lagerbestandes ist entscheidend um Engpässe vorherzusagen und die richtige Bestellmenge kalkulieren zu können.

<img class="screenshot" alt="Projected Quantity" src="{{docs_base_url}}/assets/img/stock/projected-quantity-stock-report.png">

> Projizierte Menge = Momentan vorhandene Menge + Geplante Menge + Angefragte Menge + Bestellte Menge - Reservierte Menge

* **Momentan vorhande Menge:** Menge die im Lager verfügbar ist.
* **Geplante Menge:** Menge für die ein Fertigungsauftrag ausgegeben wurde, der aber noch auf die Fertigung wartet.
* **Angefragte Menge:** Menge die vom Einkauf angefragt, aber noch nicht bestellt wurde.
* **Bestellte Menge:** Bei Lieferanten bestellte Menge, die aber noch nicht im Lager eingetroffen ist.
* **Reservierte Menge:** Von Kunden bestellte Menge, die noch nicht ausgeliefert wurde. 

{next}
