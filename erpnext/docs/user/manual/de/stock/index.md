# Lager
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Die meisten kleinen Unternehmen, die mit physischen Waren handeln, investieren einen großen Teil ihres Kapitals in Lagerbestände.

### Materialfluß

Es gibt drei Haupttypen von Buchungen:

* Kaufbeleg: Artikel die das Unternehmen von Lieferanten aufgrund einer Einkaufsbestellung erhält.
* Lagerbuchung: Artikel, die von einem Lager in ein anderes Lager übertragen werden.
* Lieferschein: Artikel, die an Kunden versandt wurden.

### Wie verfolgt ERPNext Lagerbewegungen und Lagerstände?

Das Lager abzubilden bedeutet nicht nur, Mengen zu addieren und subtrahieren. Schwierigkeiten treten dann auf, wenn:

* Zurückdatierte (vergangene) Buchungen getätigt/geändert werden: Dies wirkt sich auf zukünftige Lagerstände aus und könnte zu negativen Beständen führen.
* Das Lager basierend auf der FIFO(Firts-in-first-out)-Methode bewertet werden soll: ERPNext benötigt eine Reihenfolge aller Transaktionen, um den exakten Wert Ihrer Artikel ermitteln zu können.
* Lagerberichte zu einem beliebigen Zeitpunkt in der Vergangenheit benötigt werden: Wenn Sie für Artikel X zu einem Zeitpunkt Y die Menge/den Wert in ihrem Lager nachvollziehen müssen.

Um dies umzusetzen, sammelt ERPNext alle Bestandstransaktionen in einer Tabelle, die als Lagerhauptbuch bezeichnet wird. Alle Kaufbelege, Lagerbuchungen und Lieferscheine aktualisieren diese Tabelle.

### Themen

{index}
