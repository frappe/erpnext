# Bestandsabgleich bei nichtserialisierten Artikeln
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Bestandsabgleich ist der Prozess über den der Lagerbestand gezählt und bewertet wird. Er wird normalerweise zum Ende des Geschäftsjahres durchgeführt um den Gesamtwert des Lagers für die Abschlussbuchung zu ermitteln. In diesem Prozess werden die tatsächlichen Lagerbestände geprüft und im System aufgezeichnet. Der tatsächliche Lagerbestand und der Lagerbestand im System sollten übereinstimmen oder zumindest ähnlich sein. Wenn sie das nicht sind, können Sie das Werkzeug zum Bestandsabgleich verwenden, um den Lagerbestand und den Wert mit den tatsächlichen Begebenheiten in Einklang zu bringen.

#### Unterschied zwischen serialisierten und nicht-serialisierten Artikeln

Eine Seriennummer ist eine eindeutige Nummer oder Gruppe von Nummern und Zeichen zur Identifizierung eines individuellen Artikels. Serialisierte Artikel sind gewöhnlicherweise Artikel mit hohem Wert, für die es Garantien und Servicevereinbarungen gibt. Die meisten Artikel aus den Bereichen Maschinen, Geräte und hochwertige Elektronik (Computer, Drucker, usw.) haben Seriennummern.

Nicht serialisierte Artikel sind normalerweise Schnelldreher und von geringem Wert und brauchen aus diesem Grund keine Nachverfolgbarkeit für jedes Stück. Artikel wie Schrauben, Putztücher, Verbrauchsmaterialien und ortsgebundene Produkte können in die nichtserialisierten Artikel eingeordnet werden.

> Die Option Bestandsabgleich ist nur bei nichtserialisierten Artikeln verfügbar. Für serialisierte und Chargen-Artikel sollten Sie im Formular "Lagerbuchung" eine Materialentnahmebuchung erstellen.

### Eröffnungsbestände

Sie können einen Eröffnungsbestand über den Bestandsabgleich ins System hochladen. Der Bestandsabgleich aktualisiert Ihren Lagerbestand für einen vorgegebenen Artikel zu einem vorgegebenen Datum auf einem vorgegebenen Lager in der vorgegebenen Menge.

Um einen Lagerabgleich durchzuführen, gehen Sie zu:

> Lagerbestand > Werkzeuge > Bestandsableich > Neu

#### Schritt 1: Vorlage herunterladen

Sie sollten sich an eine spezielle Vorlage eines Tabellenblattes halten um den Bestand und den Wert eines Artikels zu importieren. Öffnen Sie ein neues Formular zum Bestandsabgleich um die Optionen für den Download zu sehen.

<img class="screenshot" alt="Bestandsabgleich" src="/docs/assets/img/setup/stock-recon-1.png">

#### Schritt 2: Geben Sie Daten in die CSV-Datei ein.

<img class="screenshot" alt="Bestandsabgleich" src="/docs/assets/img/setup/stock-reco-data.png">

Das CSV-Format beachtet Groß- und Kleinschreibung. Verändern Sie nicht die Kopfbezeichnungen, die in der Vorlage vordefiniert wurden. In den Spalten "Artikelnummer" und "Lager" geben Sie bitte die richtige Artikelnummer und das Lager ein, so wie es in ERPNext bezeichnet wird. Für die Menge geben Sie den Lagerbestand, den Sie für diesen Artikel erfassen wollen, in einem bestimmten Lager ein. Wenn Sie die Menge oder den wertmäßigen Betrag eines Artikels nicht ändern wollen, dann lassen Sie den Eintrag leer.
Anmerkung: Geben Sie keine "0" ein, wenn sie die Menge oder den wertmäßigen Betrag nicht ändern wollen. Sonst kalkuliert das System eine Menge von "0". Lassen Sie also das Feld leer!

#### Schritt 3: Laden Sie die Datei hoch und geben Sie in das Formular "Bestandsableich" Werte ein.

<img class="screenshot" alt="Bestandsabgleich" src="/docs/assets/img/setup/stock-recon-2.png">

##### Buchungsdatum

Das Buchungsdatum ist das Datum zu dem sich der hochgeladene Lagerbestand im Report wiederspiegeln soll. Die Auswahl der Option "Buchungsdatum" ermöglicht es Ihnen auch rückwirkende Bestandsabgleiche durchzuführen.

##### Konto für Bestandsveränderungen

Wenn Sie einen Bestandsabgleich durchführen um einen **Eröffnungsbestand** zu übertragen, dann sollten Sie ein Bilanzkonto auswählen. Standardmäßig wird ein **temporäres Eröffnungskonto** im Kontenplan erstellt, welches hier verwendet werden kann.

Wenn Sie einen Bestandsabgleich durchführen um den **Lagerbestand oder den Wert eines Artikels zu korrigieren**, können Sie jedes beliebige Aufwandskonto auswählen, auf das Sie den Differenzbetrag (, den Sie aus der Differenz der Werte des Artikels erhalten,) buchen wollen. Wenn das Aufwandskonto als Konto für Bestandsveränderungen ausgewählt wird, müssen Sie auch eine Kostenstelle angeben, da diese bei Ertrags- und Aufwandskonten zwingend erforderlich ist.

Wenn Sie sich die abgespeicherten Bestandsabgleichdaten noch einmal angesehen haben, übertragen Sie den Bestandsabgleich. Nach der erfolgreichen Übertragung, werden die Daten im System aktualisiert. Um die übertragenen Daten zu überprüfen gehen Sie zum Lager und schauen Sie sich den Bericht zum Lagerbestand an.

Notiz: Wenn Sie die bewerteten Beträge eines Artikels eingeben, können Sie zum Lagerbestand gehen und auf den Bericht zu den Artikelpreisen klicken, wenn Sie die Bewertungsbeträge der einzelnen Artikel herausfinden wollen. Der Bericht zeigt Ihnen alle Typen von Beträgen.

#### Schritt 4: Überprüfen Sie die Daten zum Bestandsabgleich

<img class="screenshot" alt="Bestandsabgleich Überprüfung" src="/docs/assets/img/setup/stock-reco-upload.gif">

### Bericht zum Lagerbuch

<img class="screenshot" alt="Bestandsabgleich" src="/docs/assets/img/setup/stock-reco-ledger.png">


##### So arbeitet der Bestandsabgleich

Ein Bestandsabgleich zu einem bestimmten Termin bedeutet die gesperrte Menge eines Artikels an einem bestimmten Abgleichsdatum abzugleichen, und sollte deshalb nicht im Nachhinein noch von Lagerbuchungen beeinträchtigt werden.

Beispiel:

Artikelnummer: ABC001, Lager: Mumbai. Nehmen wir an, dass der Lagerbestand zum 10. Januar 100 Stück beträgt. Zum 12. Januar wird ein Bestandsabgleich durchgeführt um den Bestand auf 150 Stück anzuheben. Das Lagerbuch sieht dann wie folgt aus:

<html>
 <table border="1" cellspacing="0px">
            <tbody>
                <tr align="center" bgcolor="#EEE">
                    <td><b>Buchungsdatum</b>
                    </td>
                    <td><b>Menge</b>
                    </td>
                    <td><b>Bestandsmenge</b>
                    </td>
                    <td><b>Belegart</b>
                    </td>
                </tr>
                <tr>
                    <td>10.01.2014</td>
                    <td align="center">100</td>
                    <td>100&nbsp;</td>
                    <td>Kaufbeleg</td>
                </tr>
                <tr>
                    <td>12.01.2014</td>
                    <td align="center">50</td>
                    <td>150</td>
                    <td>Bestandsabgleich</td>
                </tr>
            </tbody>
        </table>
</html>

Nehmen wir an, dass zum 5. Januar 2014 eine Buchung zu einem Kaufbeleg erfolgt. Das liegt vor dem Bestandsabgleich.

<html>
	<table border="1" cellspacing="0px">
        <tbody>
            <tr align="center" bgcolor="#EEE">
                <td><b>Buchungsdatum</b></td>
                <td><b>Menge</b></td>
                <td><b>Bestandsmenge</b></td>
                <td><b>Belegart</b></td>
            </tr>
            <tr>
                <td>05.01.2014</td>
                <td align="center">20</td>
                <td style="text-align: center;">20</td>
                <td>Kaufbeleg</td>
            </tr>
            <tr>
                <td>10.01.2014</td>
                <td align="center">100</td>
                <td style="text-align: center;">120</td>
                <td>Kaufbeleg</td>
            </tr>
            <tr>
                <td>12.01.2014</td>
                <td align="center"><br></td>
                <td style="text-align: center;"><b>150</b></td>
                <td>Bestandsabgleich<br></td>
            </tr>
        </tbody>
	</table>
</html>

Nach der Aktualisierungslogik wird der Kontostand, der durch den Bestandsabgleich ermittelt wurde, nicht beeinträchtigt, ungeachtet der Zugangsbuchung für den Artikel.

> Sehen Sie hierzu die Videoanleitung auf https://www.youtube.com/watch?v=0yPgrtfeCTs

{next}
