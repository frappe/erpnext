# Lieferantenauftrag
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Ein Lieferantenauftrag verhält sich analog zu einem Kundenauftrag. Normalerweise handelt es sich um einen bindenden Vertrag mit Ihrem Lieferanten bei dem Sie versichern eine Anzahl von Artikeln zu den entsprechenden Bedingungen zu kaufen.

Ein Lieferantenauftrag kann automatisch aus einer Materialanfrage oder einem Lieferantenangebot erstellt werden.

### Flußdiagramm der Lieferantenbestellung

<img class="screenshot" alt="Lieferantenauftrag" src="{{docs_base_url}}/assets/img/buying/purchase-order-f.jpg)">

In ERPNext können Sie einen Lieferantenauftrag auch direkt erstellen über:

> Einkauf > Dokumente > Lieferantenauftrag > Neuer Lieferantenauftrag

### Einen Lieferantenauftrag erstellen

<img class="screenshot" alt="Lieferantenauftrag" src="{{docs_base_url}}/assets/img/buying/purchase-order.png">

Einen Lieferantenauftrag einzugeben ist sehr ähnlich zu einer Lieferantenanfrage. Zusätzlich müssen Sie Folgendes eingeben:

* Lieferant
* Für jeden Artikel das Datum, an dem Sie ihn brauchen: Wenn Sie eine Teillieferung erwarten, weis Ihr Lieferant, welche Menge an welchem Datum geliefert werden muss. Das hilft Ihnen dabei eine Überversorgung zu vermeiden. Weiterhin hilft es Ihnen nachzuvollsziehen, wie gut sich Ihr Lieferant an Termine hält.

### Steuern

Wenn Ihnen Ihr Lieferant zusätzliche Steuern oder Abgaben wie Versandgebühren und Versicherung in Rechnung stellt, können Sie das hier eingeben. Das hilft Ihnen dabei die Kosten angemessen mitzuverfolgen. Außerdem müssen Sie Abgaben, die sich auf den Wert des Produktes auswirken, in der Steuertabelle mit berücksichtigen. Sie können für Ihre Steuern auch Vorlagen verwenden. Für weitergehende Informationen wie man Steuern einstellt lesen Sie bitte unter "Vorlage für Einkaufssteuern und Gebühren" nach.

### Mehrwertsteuern (MwSt)

Oft entspricht die Steuer, die Sie für Artikel dem Lieferanten zahlen, derselben Steuer die Ihre Kunden an Sie entrichten. In vielen Regionen ist das, was Sie als Steuer an den Staat abführen, nur die Differenz zwischen dem, was Sie von Ihren Kunden als Steuer bekommen, und dem was Sie als Steuer an Ihren Lieferanten zahlen. Das nennt man Mehrwertsteuer (MwSt).

Beispiel: Sie kaufen Artikel im Wert X ein und verkaufen Sie für 1,3x X. Somit zahlt Ihr Kunde 1,3x den Betrag, den Sie an Ihren Lieferanten zahlen. Da Sie ja für X bereits Steuer über Ihren Lieferanten gezahlt haben, müssen Sie nurmehr die Differenz von 0,3x X an den Staat abführen.

Das kann in ERPNext sehr einfach mitprotokolliert werden, das jede Steuerbezeichnung auch ein Konto ist. Im Idealfall müssen Sie für jede Mehrwertsteuerart zwei Konten erstellen, eines für Einnahmen und eines für Ausgaben, Vorsteuer (Forderung) und Umsatzsteuer (Verbindlichkeit), oder etwas ähnliches. Nehmen Sie hierzu mit Ihrem Steuerberater Kontakt auf, wenn Sie weiterführende Hilfe benötigen, oder erstellen Sie eine Anfrage im Forum.

### Umrechnung von Einkaufsmaßeinheit in Lagermaßeinheit

Sie können Ihre Maßeinheit in der Lieferantenbestellung abändern, wenn es so vom Lager gefordert wird.

Beispiel: Wenn Sie Ihr Rohmaterial in großen Mengen in Großverpackungen eingekauft haben, aber in kleinteiliger Form einlagern wollen (z. B. Kisten und Einzelteile). Das können Sie einstellen, während Sie Ihre Lieferantenbestellung erstellen.

**Schritt 1:*** Im Artikelformular Lagermaßeinheit auf Stück einstellen.

> Anmerkung: Die Maßeinheit im Artikelformular ist die Lagermaßeinheit.

**Schritt 2:** In der Lieferantenbestellung stellen Sie die Maßeinheit als Boxen ein (wenn das Material in Kisten angeliefert wird).

**Schritt 3:** Im Bereich Lager und Referenz wird die Maßeinheit als Stückzahl (aus dem Artikelformular) angezogen.

### Abbildung 3: Umrechung von Einkaufsmaßeinheit in Lagermaßeinheit

<img class="screenshot" alt="Lieferantenauftrag - Maßeinheit" src="{{docs_base_url}}/assets/img/buying/purchase-order-uom.png">

**Schritt 4:** Geben Sie den Umrechnungsfaktor von einer in die andere Maßeinheit an. Beispiel: 100, wenn eine Kiste 100 Stück umfasst.

**Schritt 5:** Die Lagermenge wird dementsprechend angepasst.

**Schritt 6:** Speichern und übertragen Sie das Formular.

{next}
