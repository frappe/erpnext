# Bewertung des Lagerbestandes
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Der Wert des verfügbaren Lagerbestandes wird im Kontenplan des Unternehmens als Vermögenswert behandelt. Abhängig von der Art der Artikel wird hier zwischen Anlagevermögen und Umlaufvermögen unterschieden. Um eine Bilanz vorzubereiten, sollten Sie die Buchungen für diese Vermögen erstellen. Es gibt generell zwei unterschiedliche Methoden den Lagerbestand zu bewerten:

### Ständige Inventur

Bei diesem Prozess bucht das System jede Lagertransaktion um Lagerbestand und Buchbestand zu synchronisieren. Das ist die Standardeinstellung in ERPNext für neue Konten.

Wenn Sie Artikel kaufen und erhalten, werden diese Artikel als Vermögen des Unternehmens gebucht (Warenbestand/Anlagevermögen). Wenn Sie diese Artikel wieder verkaufen und ausliefern, werden Kosten (Selbstkosten) in Höhe der Bezugskosten der Artikel verbucht. Nach jeder Lagertransaktion werden Buchungen im Hauptbuch erstellt. Dies hat zum Ergebnis, dass der Wert im Lagerbuch immer gleich dem Wert in der Bilanz bleibt. Das verbessert die Aussagekraft der Bilanz und der Gewinn- und Verlustrechnung.

Um Buchungen für bestimmte Lagertransaktionen zu überprüfen, bitte unter [Beispiele]({{docs_base_url}}/user/manual/de/stock/accounting-of-inventory-stock/perpetual-inventory.html) nachlesen.

#### Vorteile

Das System der laufenden Inventur macht es Ihnen leichter eine exakte Aussage über Vermögen und Kosten zu erhalten. Die Lagerbilanz wird ständig mit den relevanten Kontoständen abgeglichen, somit müssen keine manuellen Buchungen mehr für jede Periode erstellt werden, um die Salden auszugleichen.

Für den Fall, dass neue zurückdatierte Transaktionen erstellt werden oder Stornierungen von bereits angelegten Transaktionen statt finden, werden für alle Artikel dieser Transaktion alle Buchungen im Lagerbuch und Hauptbuch, die danach liegen, neu berechnet. Auf dieselbe Vorgehensweise wird zurück gegriffen, wenn Kosten zum übertragenen Kaufbeleg hinzugefügt werden, nachgereicht über das Hilfsprogramm für Einstandskosten.

> Anmerkung: Die ständige Inventur hängt vollständig von der Artikelbewertung ab. Deshalb müssen Sie bei der Eingabe der Werte vorsichtiger vorgehen, wenn Sie gleichzeitig annehmende Lagertransaktionen wie Kaufbeleg, Materialschein oder Fertigung/Umpacken erstellen.

---

### Stichtagsinventur

Bei dieser Methode werden periodisch manuelle Buchungen erstellt, um die Lagerbilanz und die relevanten Kontenstände abzugleichen. Das System erstellt die Buchungen für Vermögen zum Zeitpunkt des Materialeinkaufs oder -verkaufs nicht automatisch.

Während einer Buchungsperiode werden Kosten in ihrem Buchhaltungssystem gebucht, wenn Sie Artikel kaufen und erhalten. Einen Teil dieser Artikel verkaufen und liefern Sie dann aus.

Am Ende einer Buchungsperiode muss dann der Gesamtwert der verkauften Artikel als Unternehmensvermögen (oft als Warenbestand) gebucht werden.

Die Differenz aus dem Wert der Waren, die noch nicht verkauft wurden, und dem Warenbestand zum Ende der letzten Periode kann positiv oder negativ sein und wird dem Vermögen (Warenbestand/Anlagevermögen) hinzugefügt. Wenn es sich um einen negativen Betrag handelt, erfolgt die Buchung spiegelverkehrt.

Dieser Gesamtprozess wird als Stichtagsinventur bezeichnet.

Wenn Sie als bereits existierender Benutzer die Stichtagsinventur nutzen aber zur Ständigen Inventur wechseln möchten, müssen Sie der Migrationsanleitung folgen. Für weitere Details lesen Sie [Migration aus der Stichtagsinventur]({{docs_base_url}}/user/manual/de/stock/accounting-of-inventory-stock/migrate-to-perpetual-inventory.html).

{next}
