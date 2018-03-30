# Artikel
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Ein Artikel ist ein Produkt oder eine Dienstleistung Ihres Unternehmens. Die Bezeichnung Artikel ist genauso anwendbar auf Ihre Kernprodukte wie auch auf Ihr Rohmaterial. Es kann ein Produkt oder eine Dienstleistung sein, welche Sie von Lieferanten kaufen/an Kunden verkaufen. ERPNext versetzt sie in die Lage alle Arten von Artikeln wie Rohmaterial, Unterbeauftragungen, Fertigprodukte, Artikelvarianten und Dienstleistungsartikel zu verwalten.
ERPNext ist auf die artikelbezogene Verwaltung Ihrer Ver- und Einkäufe optimiert. Wenn Sie sich im Bereich Dienstleistungen befinden, können Sie für jede Dienstleistung, die Sie anbieten, einen eigenen Artikel erstellen. Die Artikelstammdaten zu vervollständigen ist für eine erfolgreiche Einführung von ERPNext ausschlaggebend.

### Artikeleigenschaften

* **Artikelname:** Artikelname ist der tatsächliche Name Ihres Artikels oder Ihrer Dienstleistung.
* **Artikelcode:** Der Artikelcode ist eine Kurzform um Ihren Artikel zu beschreiben. Wenn Sie sehr wenig Artikel haben, ist es ratsam den Artikelnamen und den Artikelcode gleich zu halten. Das hilft neuen Nutzern dabei, Artikeldetails in allen Transaktionen zu erkennen und einzugeben. Für den Fall, dass Sie sehr viele Artikel mit langen Namen haben, und die Anzahl in die Hunderte geht, ist es ratsam, zu kodieren. Um die Benamung der Artikelcodes zu verstehen, lesen Sie bitte den Bereich "Artikel-Kodierung".
* **Artikelgruppe:** Artikelgruppe wird verwendet um einen Artikel nach verschiedenen Kriterien zu kategorisieren, wie zum Beispiel Produkte, Rohmaterial, Dienstleistungen, Unterbeauftragungen, Verbrauchsgüter oder alle Artikelgruppen. Erstellen Sie Ihre Standard-Artikelgruppen-Liste unter Lagerbestand > Einstellungen > Artikelgruppenstruktur und stellen Sie diese Option vorein, während Sie die Details zu Ihren neuen Artikeln unter Artikelgruppe eingeben.
* **Standardmaßeinheit:** Das ist die Standardmaßeinheit, die in Verbindung mit Ihrem Produkt verwendet wird. Hierbei kann es sich um Stückzahl, kg, Meter, usw. handeln. Sie können alle Standardmaßeinheiten, die Ihr Produkt benötigt, unter Einstellungen > Lagerbestand > Einstellungen > Maßeinheit ablegen. Für das Eingeben von neuen Artikeln kann eine Voreinstellung getroffen werden, indem man % drückt um eine Popup-Liste der Standardmaßeinheiten zu erhalten.
* **Marke:** Wenn Sie mehr als eine Marke haben, speichern Sie diese bitte unter Lagerbestand > Einstellungen > Marke und stellen Sie diese vorein, während Sie neue Artikel erstellen.
* **Variante:** Eine Artikelvariante ist eine Abwandlung eines Artikels. Um mehr über die Verwaltung von Varianten zu erfahren, lesen Sie bitte "Artikelvarianten".

### Ein Bild hochladen
Um für Ihr Icon ein Bild hochzuladen, das in allen Transaktionen erscheint, speichern Sie bitte das teilweise ausgefüllte Formular. Nur dann, wenn die Datei abgespeichert wurde, ist die "Hochladen"-Schaltfläche über dem Bildsymbol verwendbar. Klicken Sie auf dieses Symbol und laden Sie das Bild hoch.

### Lagerbestand: Lager- und Bestandseinstellungen

In ERPNext können Sie verschiedene Typen von Lagern einstellen um Ihre unterschiedlichen Artikel zu lagern. Die Auswahl kann aufgrund der Artikeltypen getroffen werden. Das kann ein Artikel des Anlagevermögens sein, ein Lagerartikel oder auch ein Fertigungsartikel.

* **Lagerartikel:** Wenn Sie Lagerartikel dieses Typs in Ihrem Lagerbestand verwalten, erzeugt ERPNext für jede Transaktion dieses Artikels eine Buchung im Lagerhauptbuch.
* **Standardlager:** Das ist das Lager, welches automatisch bei Ihren Transaktionen ausgewählt wird.
* **Erlaubter Prozentsatz:** Das ist der Prozentsatz der angibt, wieviel Sie bei einem Artikel überberechnen oder überliefern dürfen. Wenn er nicht vorgegeben ist, wird er aus den globalen Einstellungen übernommen.
* **Bewertungsmethode:** Es gibt zwei Möglichkeiten den Lagerbestand zu bewerten. FIFO (first in - first out) und Gleitender Durchschnitt. Um dieses Thema besser zu verstehen, lesen Sie bitte "Artikelbewertung, FIFO und Gleitender Durchschnitt".

### Serialisierter und chargenbezogener Lagerbestand

Die Nummerierungen helfen dabei einzelne Artikel oder Chargen individuell nachzuverfolgen. Ebenso können Garantieleistungen und Rückläufe nachverfolgt werden. Für den Fall, dass ein bestimmter Artikel von einem Lieferanten zurück gerufen wird, hilft die Nummer dabei, einzelne Artikel nachzuverfolgen. Das Nummerierungssystem verwaltet weiterhin das Verfalldatum. Bitte beachten Sie, dass Sie Ihre Artikel nicht serialisieren müssen, wenn Sie die Artikel zu Tausenden verkaufen, und sie sehr klein sind, wie z. B. Stifte oder Radiergummis. In der ERPNext-Software müssen Sie die Seriennummer bei bestimmten Buchungen mit angeben. Um Seriennummern zu erstellen, müssen Sie die Seriennummern per Hand in Ihren Buchungen eintragen. Wenn es sich nicht um ein großes und haltbares Verbrauchsgut handelt, es keine Garantie hat und die Möglichkeit eines Rückrufs äußerst gering ist, sollten Sie eine Seriennummerierung vermeiden.

> Wichtig: Sobald Sie einen Artikel als serialisiert oder als Charge oder beides markiert haben, können Sie das nicht mehr ändern, nachdem Sie eine Buchung erstellt haben.

### Diskussion zu serialisiertem Lagerbestand

### Automatische Nachbestellung

* **Meldebestand** bezeichnet eine definierte Menge an Artikeln im Lager, bei der nachbestellt wird.
* **Nachbestellmenge** bezeichnet die Menge an Artikeln die bestellt werden muss, um einen bestimmtem Lagerbestand zu erreichen.
* **Mindestbestellmenge** ist die kleinstmögliche Menge, für die eine Materialanfrage / eine Einkaufsbestellung ausgelöst werden kann.

### Artikelsteuer

Diese Einstellungen werden nur dann benötigt, wenn ein bestimmter Artikel einer anderen Besteuerung unterliegt als derjenigen, die im Standard-Steuerkonto hinterlegt ist. Beispiel: Wenn Sie ein Steuerkonto "Umsatzsteuer 19%" haben, und der Artikel, um den es sich dreht, von der Steuer ausgenommen ist, dann wählen Sie "Umsatzsteuer 19%" in der ersten Spalte und stellen als Steuersatz in der zweiten Spalte "0" ein.

Lesen Sie im Abschnitt "Steuern einstellen" weiter, wenn Sie mehr Informationen wünschen.

## Prüfkriterien

* **Kontrolle erforderlich:** Wenn für einen Artikel eine Wareneingangskontrolle (zum Zeitpunkt der Anlieferung durch den Lieferanten) zwingend erforderlich ist, aktivieren Sie "Ja" bei den Einstellungen für "Prüfung erforderlich". Das Sytem stellt sicher, dass eine Qualitätskontrolle vorbereitet und durchgeführt wird bevor ein Kaufbeleg übertragen wird.
* **Kontrollkriterien:** Wenn eine Qualitätsprüfung für den Artikel vorbereitet wird, dann wird die Vorlage für die Kriterien automatisch in der Tabelle Qualitätskontrolle aktualisiert. Beispiele für Kriterien sind: Gewicht, Länge, Oberfläche usw.

## Einkaufsdetails
* **Lieferzeit in Tagen:** Die Lieferzeit in Tagen bezeichnet die Anzahl der Tage die benötigt werden bis der Artikel das Lager erreicht.
* **Standard-Aufwandskonto:** Dies ist das Konto auf dem die Kosten für den Artikel verzeichnet werden.
* **Standard-Einkaufskostenstelle:** Sie wird verwendet um die Kosten für den Artikel nachzuverfolgen.

## Verkausdetails
* **Standard-Ertragskonto:** Das hier gewählte Ertragskonto wird automatisch mit der Ausgangsrechung für diesen Artikel verknüpft.
* **Standard-Vertriebskostenstelle:** Die hier gewählte Kostenstelle wird automatisch mit der Ausgangsrechnung für diesen Artikel verknüpft.

## Fertigung und Webseite

Lesen Sie in den Abschnitten "Fertigung" und "Webseite" nach, um weitere Informationen zu diesen Themen zu erhalten.

{next}
