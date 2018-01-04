# Charge
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Die Funktion Chargenverwaltung in ERPNext versetzt Sie in die Lage, verschiedene Einheiten eines Artikels zu gruppieren und ihnen eine einzigartige Nummer, die man Chargennummer nennt, zuzuweisen.

Die Vorgehensweise, das Lager chargenbasiert zu verwalten, wird hauptsächlich in der pharmazeutischen Industrie angewandt. Medikamenten wird hier chargenbasiert eine eindeutige ID zugewiesen. Das hilft dabei, das Verfallsdatum der in einer bestimmten Charge produzierten Mengen aktuell zu halten und nachzuvollziehen.

> Anmerkung: Um einen Artikel als Chargenartikel zu kennzeichnen, muss in den Artikelstammdaten das Feld "Hat Chargennummer" markiert werden.

Bei jeder für einen Chargenartikel generierten Lagertransaktion (Kaufbeleg, Lieferschein, POS-Rechnung) sollten Sie die Chargennummer des Artikels mit angeben. Um eine neue Chargennummer für einen Artikel zu erstellen, gehen Sie zu:

> Lagerbestand > Dokumente > Charge > Neu

Die Chargenstammdaten werden vor der Ausfertigung des Kaufbelegs erstellt. Somit erstellen Sie immer dann, wenn für einen Chargenartikel ein Kaufbeleg oder ein Produktionsauftrag ausgegeben werden, zuerst die Chargennummer des Artikels und wählen diese dann im Kaufbeleg oder im Produktionsauftrag aus.

<img class="screenshot" alt="Charge" src="/docs/assets/img/stock/batch.png">

> Anmerkung: Bei Lagertransaktionen werden die Chargen-IDs basierend auf dem Code, dem Lager, dem Verfallsdatum der Charge (verglichen mit dem Veröffentlichungsdatum der Transaktion) und der aktuellen Menge im Lager gefiltert.

{next}
