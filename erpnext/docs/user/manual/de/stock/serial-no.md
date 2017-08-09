# Seriennummer
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Wie bereits im Abschnitt **Artikel** besprochen, wird ein Datensatz **Seriennummer** (S/N) für jede Menge eines Artikels vorgehalten, wenn ein **Artikel serialisiert** wird. Diese Information ist hilfreich um den Standort der Seriennummer nachzuvollziehen, wenn es um Garantiethemen geht und um Informationen zur Lebensdauer (Verfallsdatum).

**Seriennummern** sind auch dann nützlich, wenn es darum geht, das Anlagevermögen zu verwalten. Zudem können **Wartungspläne** unter Zuhilfenahme von Seriennummern erstellt werden um Wartungsarbeiten für Anlagen zu planen und zu terminieren (sofern sie Wartung benötigen).

Sie können auch nachvollziehen von welchem **Lieferanten** Sie eine bestimmte **Seriennummer** gekauft haben und welchem **Kunden** Sie diese verkauft haben. Der Status der **Seriennummer** verrät Ihnen den aktuellen Lagerbestands-Status.

Wenn Ihr Artikel serialisiert ist, müssen Sie die Seriennummern in der entsprechenden Spalte eintragen, jede in eine neue Zeile. Sie können einzelne Einheiten von serialisierten Artikeln über die Seriennummern verwalten.

### Seriennummern und Lagerbestand

Der Lagerbestand eines Artikels kann nur dann beeinflusst werden, wenn die Seriennummer mit Hilfe einer Lagertransaktion (Lagerbuchung, Kaufbeleg, Lieferschein, Ausgangsrechnung) übertragen wird. Wenn eine neue Seriennummer direkt erstellt wird, kann der Lagerort nicht eingestellt werden.

<img class="screenshot" alt="Seriennummer" src="/docs/assets/img/stock/serial-no.png">

* Der Status wird aufgrund der Lagerbuchung eingestellt.
* Nur Seriennummern mit dem Status "Verfügbar" können geliefert werden.
* Seriennummern können automatisch aus einer Lagerbuchung oder aus einem Kaufbeleg heraus erstellt werden. Wenn Sie "Seriennummer" in der Spalte "Seriennummer" aktivieren, werden diese Seriennummern automatisch erstellt.
* Wenn in den Artikelstammdaten "Hat Seriennummer" aktiviert wird, können Sie die Spalte "Seriennummer" in der Lagerbuchung/im Kaufbeleg leer lassen und die Seriennummern werden automatisch aus dieser Serie heraus erstellt.

{next}
