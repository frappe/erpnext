# Lagerbuchung
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Eine Lagerbuchung ist ein einfaches Dokument, welches Sie Lagerbewegungen aus einem Lager heraus, in ein Lager hinein oder zwischen Lagern aufzeichnen lässt.

Wenn Sie eine Lagerbuchung erstellen möchten, gehen Sie zu: 

> Lagerbestand > Dokumente > Lagerbuchung > Neu

<img class="screenshot" alt="Lagerbuchung" src="/docs/assets/img/stock/stock-entry.png">

Lagerbuchungen können aus folgenden Gründen erstellt werden:

* Materialentnahme - Wenn das Material ausgegeben wird (ausgehendes Material).
* Materialannahme - Wenn das Material angenommen wird (eingehendes Material).
* Materialübertrag - Wenn das Material von einem Lager in ein anders Lager übertragen wird.
* Materialübertrag für Herstellung - Wann das Material in den Fertigungsprozess übertragen wird.
* Herstellung - Wenn das Material von einem Fertigungs-/Produktionsarbeitsgang empfangen wird.
* Umpacken - Wenn der/die Originalartikel zu einem neuen Artikel verpackt wird/werden.
* Zulieferer - Wenn das Material aufgrund einer Untervergabe ausgegeben wird.

In einer Lagerbuchung müssen Sie die Artikelliste mit all Ihren Transaktionen aktualisieren. Für jede Zeile müssen Sie ein Ausgangslager oder ein Eingangslager oder beides eingeben (wenn Sie eine Bewegung erfassen).

#### Zusätzliche Kosten

Wenn die Lagerbuchung eine Eingangsbuchung ist, d. h. wenn ein beliebiger Artikel an einem Ziellager angenommen wird, können Sie zusätzliche Kosten erfassen (wie Versandgebühren, Zollgebühren, Betriebskosten, usw.), die mit dem Prozess verbunden sind. Die Zusatzkosten werden berücksichtigt, um den Wert des Artikels zu kalkulieren.

Um Zusatzkosten hinzuzufügen, geben Sie die Beschreibung und den Betrag der Kosten in die Tabelle Zusatzkosten ein.

<img class="screenshot" alt="Lagerbuchung Zusatzlkosten" src="/docs/assets/img/stock/additional-costs-table.png">

Die hinzugefügten Zusatzkosten werden basierend auf dem Grundwert der Artikel proportional auf die erhaltenen Artikel verteilt. Dann werden die verteilten Zusatzkosten zum Grundpreis hinzugerechnet, um den Wert neu zu berechnen.

<img class="screenshot" alt="Lagerbuchung Preis für Artikelvarianten" src="/docs/assets/img/stock/stock-entry-item-valuation-rate.png">

Wenn die laufende Inventur aktiviert ist, werden Zusatzkosten auf das Konto "Aufwendungen im Wert beinhaltet" gebucht.

<img class="screenshot" alt="Zusatzkosten Hauptbuch" src="/docs/assets/img/stock/additional-costs-general-ledger.png">
> Hinweis: Um den Lagerbestand über eine Tabellenkalkulation zu aktualisieren, bitte unter Lagerabgleich nachlesen.

{next}
