# Lieferantenreklamation
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

In ERPNext gibt es eine Option für Produkte, die zurück zum Lieferanten geschickt werden müssen. Die Gründe dafür können vielfältig sein, z. B. defekte Waren, nicht ausreichende Qualität, der Käufer braucht die Ware nicht (mehr), usw.

Sie können eine Lieferantenreklamation erstellen indem Sie ganz einfach einen Kaufbeleg mit negativer Menge erstellen.

Öffnen Sie hierzu zuerst die ursprüngliche Eingangsrechnung zu der der Lieferant die Artikel geliefert hat.

<img class="screenshot" alt="Original-Eingangsrechnung" src="{{docs_base_url}}/assets/img/stock/purchase-return-original-purchase-receipt.png">

Klicken Sie dann auf "Lieferantenreklamation erstellen", dies öffnet einen neuen Kaufbeleg bei dem "Ist Reklamation" markiert ist, und bei dem die Artikel mit negativer Menge aufgeführt sind.

<img class="screenshot" alt="Reklamation zum Lieferschein" src="{{docs_base_url}}/assets/img/stock/purchase-return-against-purchase-receipt.png">

Bei der Ausgabe eines Reklamations-Kaufbelegs vermindert das System die Menge des Artikels auf dem entsprechenden Lager. Um einen korrekten Lagerwert zu erhalten, verändert sich der Lagersaldo entsprechend dem Einkaufspreis des zurückgesendeten Artikels.

<img class="screenshot" alt="Reklamation und Lagerbuch" src="{{docs_base_url}}/assets/img/stock/purchase-return-stock-ledger.png">

Wenn die Ständige Inventur aktiviert wurde, verbucht das System weiterhin Buchungssätze zum Lagerkonto um den Lagersaldo  mit dem Lagerbestand des Lagerbuchs zu synchronisieren.

<img class="screenshot" alt="Reklamation und Lagerbuch" src="{{docs_base_url}}/assets/img/stock/purchase-return-general-ledger.png">

{next}
