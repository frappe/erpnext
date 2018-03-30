# Ständige Inventur
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

In der Ständigen Inventur erstellt das System Buchungen für jede Lagertransaktion, so dass das Lager und der Kontostand immer synchron bleiben. Der Kontostand wird für jedes Lager mit der zutreffenden  Kontobezeichnung verbucht. Wenn das Lager gespeichert wird, erstellt das System automatisch eine Kontobezeichnung mit dem selben Namen wie das Lager. Da für jedes Lager ein Kontostand verwaltet wird, sollten Sie Lager auf Basis der in ihnen eingelagerten Artikel (Umlaufvermögen/Anlagevermögen) erstellen.

Wenn Artikel in einem bestimmten Lager ankommen, erhöht sich der Stand des Vermögenskontos (das mit dem Lager verknüpft ist). Analog dazu wird ein Aufwand verbucht, wenn Sie Waren ausliefern, und der Stand des Vermögenskontos nimmt ab, basierend auf der Bewertung der entsprechenden Artikel. 

### Aktivierung

1. Richten Sie die folgenden Standard-Konten für jede Firma ein:
    * Lagerwaren erhalten aber noch nicht abgerechnet
    * Lagerabgleichskonto
    * In der Bewertung enthaltene Kosten
    * Kostenstelle
2. In der Ständigen Inventur verwaltet das System für jedes Lager einen eigenen Kontostand unter einer eigenen Kontobezeichnung. Um diese Kontobezeichnung zu erstellen, gehen Sie zu "Konto erstellen unter" in den Lagerstammdaten.
3. Aktivieren Sie die Ständige Inventur.

> Einstellungen > Rechnungswesen > Kontoeinstellungen > Eine Buchung für jede Lagerbewegung erstellen

---

### Beispiel

Wir nehmen folgenden Kontenplan und folgende Lagereinstellungen für Ihre Firma an:

Kontenplan

  * Vermögen (Soll) 
    * Umlaufvermögen
    * Forderungen
      * Jane Doe
    * Lagervermögenswerte
      * In Verkaufsstellen
      * Fertigerzeugnisse
      * In der Fertigung
    * Steuervermögenswerte
      * Umsatzsteuer (Vorsteuer)
    * Anlagevermögen
    * Anlagevermögen im Lager
  * Verbindlichkeiten (Haben)
    * Kurzfristige Verbindlichkeiten
    * Verbindlichkeiten aus Lieferungen und Leistungen
      * East Wind Inc.
    * Lagerverbindlichkeiten 
      * Lagerware erhalten aber noch nicht abgerechnet
    * Steuerverbindlichkeiten
      * Dienstleistungssteuer
  * Erträge (Haben)
    * Direkte Erträge
    * Verkäufe
  * Aufwendungen (Soll)
    * Direkte Aufwendungen
    * Lageraufwendungen
      * Selbstkosten
      * In der Bewertung enthaltene Kosten
      * Bestandsveränderungen
      * Versandgebühren
      * Zoll

#### Kontenkonfiguration des Lagers

* In Verkaufsstellen
* In der Fertigung
* Fertigerzeugnisse
* Anlagevermögen im Lager

#### Kaufbeleg

Nehmen wir an, Sie haben 10 Stück des Artikels "RM0001" zu 200€ und 5 Stück des Artikels "Tisch" zu **100€** vom Lieferanten "Arcu Vel Quam Fabricators" eingekauft. Im Folgenden finden Sie die Details des Kaufbelegs:

**Supplier:** Arcu Vel Quam Fabricators

**Artikel:**

<table class="table table-bordered">
    <thead>
        <tr>
            <th>Artikel</th>
            <th>Lager</th>
            <th>Menge</th>
            <th>Preis</th>
            <th>Gesamtmenge</th>
            <th>Wertansatz</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>RM0001</td>
            <td>In Verkaufsstellen</td>
            <td>10</td>
            <td>200</td>
            <td>2000</td>
            <td>2200</td>
        </tr>
        <tr>
            <td>Tisch</td>
            <td>Anlagevermögen im Lager</td>
            <td>5</td>
            <td>100</td>
            <td>500</td>
            <td>550</td>
        </tr>
    </tbody>
</table>
<p><strong>Steuern:</strong>
</p>
<table class="table table-bordered">
    <thead>
        <tr>
            <th>Konto</th>
            <th>Betrag</th>
            <th>Kategorie</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Versandgebühren</td>
            <td>100</td>
            <td>Gesamtsumme und Bewertung</td>
        </tr>
        <tr>
            <td>MwSt</td>
            <td>120</td>
            <td>Gesamtsumme</td>
        </tr>
        <tr>
            <td>Zoll</td>
            <td>150</td>
            <td>Bewertung</td>
        </tr>
    </tbody>
</table>
<p><strong>Lagerbuch</strong>
</p>

<img class="screenshot" alt="Lagerbuch" src="{{docs_base_url}}/assets/img/accounts/perpetual-receipt-sl-1.png">

**Hauptbuch:**

<img class="screenshot" alt="Hauptbuch" src="{{docs_base_url}}/assets/img/accounts/perpetual-receipt-gl-2.png">

Um ein System der doppelten Buchhaltung zu erhalten, werden dadurch, dass sich der Kontensaldo durch den Kaufbeleg erhöht, die Konten "In Verkaufsstellen" und "Anlagevermögen im Lager" belastet und das temporäre Konto "Lagerware erhalten aber noch nicht abgerechnet" entlastet. Zum selben Zeitpunkt wird eine negative Aufwendung auf das Konto "In der Bewertung enthaltene Kosten" verbucht, um die Bewertung hinzuzufügen und um eine doppelte Aufwandsverbuchung zu vermeiden.

---

### Eingangsrechnung

Wenn eine Rechnung des Lieferanten für den oben angesprochenen Kaufbeleg eintrifft, wird hierzu eine Eingangsrechnung erstellt. Die Buchungen im Hauptbuch sind folgende:

#### Hauptbuch

<img class="screenshot" alt="Hauptbuch" src="{{docs_base_url}}/assets/img/accounts/perpetual-pinv-gl-3.png">

Hier wird das Konto "Lagerware erhalten aber noch nicht bewertet" belastet und hebt den Effekt des Kaufbeleges auf.

* * *

### Lieferschein

Nehmen wir an, dass Sie eine Kundenbestellung von "Utah Automation Services" über 5 Stück des Artikels "RM0001" zu 300€ haben. Im Folgenden sehen Sie die Details des Lieferscheins.

**Kunde:** Utah Automation Services

**Artikel:**

<table class="table table-bordered">
    <thead>
        <tr>
            <th>Artikel</th>
            <th>Lager</th>
            <th>Menge</th>
            <th>Preis</th>
            <th>Summe</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>RM0001</td>
            <td>In Verkaufsstellen</td>
            <td>5</td>
            <td>300</td>
            <td>1500</td>
        </tr>
    </tbody>
</table>
<p><strong>Steuern:</strong>
</p>
<table class="table table-bordered">
    <thead>
        <tr>
            <th>Konto</th>
            <th>Menge</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Dienstleistungssteuer</td>
            <td>150</td>
        </tr>
        <tr>
            <td>MwSt</td>
            <td>100</td>
        </tr>
    </tbody>
</table>

**Lagerbuch**

<img class="screenshot" alt="Lagerbuch" src="{{docs_base_url}}/assets/img/accounts/perpetual-dn-sl-4.png">

**Hauptbuch**

<img class="screenshot" alt="Hauptbuch" src="{{docs_base_url}}/assets/img/accounts/perpetual-dn-gl-5.png">

Da der Artikel aus dem Lager "In Verkaufsstellen" geliefert wird, wird das Konto "In Verkaufsstellen" entlastet und ein Betrag in gleicher Höhe dem Aufwandskonto "Selbstkosten" belastet. Der belastete/entlastete Betrag ist gleich dem Gesamtwert (Einkaufskosten) des Verkaufsartikels. Und der Wert wird gemäß der bevorzugten Bewertungsmethode (FIFO/Gleitender Durchschnitt) oder den tatsächlichen Kosten eines serialisierten Artikels kalkuliert.

      
    In diesem Beispiel gehen wir davon aus, dass wir als Berwertungsmethode FIFO verwenden. 
    Bewertungpreis  = Einkaufpreis + In der Bewertung enthaltene Abgaben/Gebühren 
                    = 200 + (250 * (2000 / 2500) / 10) 
                    = 220
    Gesamtsumme der Bewertung = 220 * 5 
                            = 1100
        

* * *

### Ausgangsrechnung mit Lageraktualisierung

Nehmen wir an, dass Sie zur obigen Bestellung keinen Lieferschein erstellt haben sondern direkt eine Ausgangsrechnung mit der Option "Lager aktualisieren" erstellt haben. Die Details der Ausgangsrechnung sind die gleichen wie bei obigem Lieferschein.

**Lagerbuch**

<img class="screenshot" alt="Lagerbuch" src="{{docs_base_url}}/assets/img/accounts/perpetual-inv-sl-6.png">

**Hauptbuch**

<img class="screenshot" alt="Hauptbuch" src="{{docs_base_url}}/assets/img/accounts/perpetual-inv-gl-7.png">

Hier werden, im Gegensatz zu den normalen Buchungen für Rechnungen, die Konten "In Verkaufsstellen" und "Selbstkosten" basierend auf der Bewertung beeinflusst.

* * *

### Lagerbuchung (Materialschein)

**Artikel:**

<table class="table table-bordered">
    <thead>
        <tr>
            <th>Artikel/th>
            <th>Eingangslager</th>
            <th>Menge</th>
            <th>Preis</th>
            <th>Summe</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>RM0001</td>
            <td>In den Verkaufsstellen</td>
            <td>50</td>
            <td>220</td>
            <td>11000</td>
        </tr>
    </tbody>
</table>

**Lagerbuch**

<img class="screenshot" alt="Lagerbuch" src="{{docs_base_url}}/assets/img/accounts/perpetual-st-receipt-sl.png">

**Hauptbuch**

<img class="screenshot" alt="Hauptbuch" src="{{docs_base_url}}/assets/img/accounts/perpetual-st-receipt-gl.png">

* * *

### Lagerbuchung (Materialanfrage)

**Artikel:**

<table class="table table-bordered">
    <thead>
        <tr>
            <th>Artikel</th>
            <th>Ausgangslager</th>
            <th>Menge</th>
            <th>Preis</th>
            <th>Summe</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>RM0001</td>
            <td>In den Verkaufsstellen</td>
            <td>10</td>
            <td>220</td>
            <td>2200</td>
        </tr>
    </tbody>
</table>

**Lagerbuch**

<img class="screenshot" alt="Lagerbuch" src="{{docs_base_url}}/assets/img/accounts/perpetual-st-issue-sl.png">

**Hauptbuch**

<img class="screenshot" alt="Hauptbuch" src="{{docs_base_url}}/assets/img/accounts/perpetual-st-issue-gl.png">

* * *

### Lagerbuchung (Materialübertrag)

**Artikel:**

<table class="table table-bordered">
    <thead>
        <tr>
            <th>Artikel</th>
            <th>Ausgangslager</th>
            <th>Eingangslager</th>
            <th>Menge</th>
            <th>Preis</th>
            <th>Summe</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>RM0001</td>
            <td>In den Verkaufsstellen</td>
            <td>Fertigung</td>
            <td>10</td>
            <td>220</td>
            <td>2200</td>
        </tr>
    </tbody>
</table>

**Lagerbuch**

<img class="screenshot" alt="Lagerbuch" src="{{docs_base_url}}/assets/img/accounts/perpetual-st-transfer-sl.png">

**Hauptbuch**

<img class="screenshot" alt="Hauptbuch" src="{{docs_base_url}}/assets/img/accounts/perpetual-st-transfer-gl.png">