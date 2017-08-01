# Kundenauftrag
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Der Kundenauftrag bestätigt Ihren Verkauf und stößt Einkauf (**Materialanfrage**), Versand (**Lieferschein**), Abrechnung (**Ausgangsrechnung**) und Fertigung (**Produktionsplan**) an.

Ein Kundenauftrag ist normalerweise ein bindender Vertrag mit Ihrem Kunden.

Wenn Ihr Kunde das Angebot annimmt, können Sie das Angebot in einen Kundenauftrag umwandeln.

### Flußdiagramm des Kundenauftrags

<img class="screenshot" alt="Kundenauftrag aus Angebot erstellen" src="/docs/assets/img/selling/sales-order-f.jpg">

Um einen neuen Kundenauftrag zu erstellen gehen Sie zu: > Vertrieb > Kundenauftrag > Neuer Kundenauftrag

### Einen Kundenauftrag aus einem Angebot erstellen

Sie können einen Kundenauftrag auch aus einem übertragenen Angebot heraus erstellen.

<img class="screenshot" alt="Kundenauftrag aus Angebot erstellen" src="/docs/assets/img/selling/make-SO-from-quote.png">

Oder Sie erstellen einen neuen Kundenauftrag und entnehmen die Details aus dem Angebot.

<img class="screenshot" alt="Kundenauftrag aus Angebot erstellen" src="/docs/assets/img/selling/make-so.gif">

Die meisten Informationen im Kundenauftrag sind dieselben wie im Angebot. Einige Dinge möchte der Kundenauftrag aber aktualisiert haben.

* Voraussichtlicher Liefertermin
* Kundenbestellnummer: Wenn Ihnen Ihr Kunde einen Kundenauftrag geschickt hat, können Sie dessen Nummer als Refernz für die Zukunft (Abrechnung) erfassen.

### Packliste

Die Tabelle "Packliste" wird automatisch aktualisiert, wenn Sie den Kundenauftrag abspeichern. Wenn einer der Artikel in Ihrer Tabelle ein Produkt-Bundle (Paket) ist, dann enthält die Packliste eine aufgelöste Übersicht Ihrer Artikel.

### Reservierung und Lager

Wenn Ihr Kundenauftrag Artikel enthält, für die das Lager nachverfolgt wird ("Ist Lagerartikel" ist mit JA markiert), dann fragt sie ERPNext nach einem Reservierungslager. Wenn Sie ein Standard-Lager für den Artikel eingestellt haben, wird dieses automatisch verwendet.

Die "reservierte" Menge hilft Ihnen dabei, die Menge abzuschätzen, die Sie basierend auf all Ihren Verpflichtungen einkaufen müssen.

### Vertriebsteam

**Vertriebspartner:** Wenn ein Verkauf über einen Vertriebspartner gebucht wurde, können Sie die Einzelheiten des Vertriebspartners mit der Provision und anderen gesammelten Informationen aktualisieren.

**Vertriebsperson:** ERPNext erlaubt es Ihnen verschiedene Vertriebspersonen zu markieren, die an diesem Geschäft mitgearbeitet haben. Sie können auch den Anteil an der Zielerreichung auf die Vertriebspersonen aufteilen und nachverfolgen wieviele Prämien sie mit diesem Geschäft verdient haben.

### Wiederkehrende Kundenaufträge

Wenn Sie mit einem Kunden einen Serienkontrakt vereinbart haben, bei dem Sie einen monatlichen, vierteljährlichen, halbjährlichen oder jährlichen Kundenauftrag generieren müssen, können Sie hierfür "In wiederkehrende Bestellung umwandeln" aktivieren.

Hier können Sie folgende Details eingeben: Wie häufig Sie eine Bestellung generieren wollen im Feld "Wiederholungstyp", an welchem Tag des Monats die Bestellung generiert werden soll im Feld "Wiederholen an Tag des Monats" und das Datum an dem die wiederkehrenden Bestellungen eingestellt werden sollen im Feld "Enddatum".

**Wiederholungstyp:** Hier können Sie die Häufigkeit in der Sie eine Bestellung generieren wollen eingeben.

**Wiederholen an Tag des Monats:** Sie können angeben, an welchem Tag des Monats die Bestellung generiert werden soll.

**Enddatum:** Das Datum an dem die wiederkehrenden Bestellungen eingestellt werden sollen.

Wenn Sie den Kundenauftrag aktualisieren, wird eine wiederkehrende ID generiert, die für alle wiederkehrenden Bestellungen dieses speziellen Kundenauftrag gleich ist.

ERPNext erstellt automatisch eine neue Bestellung und versendet eine E-Mail-Mitteilung an die E-Mail-Konten, die Sie im Feld "Benachrichtigungs-E-Mail-Adresse" eingestellt haben.

<img class="screenshot" alt="Wiederkehrende Kundenaufträge" src="/docs/assets/img/selling/recurring-sales-order.png">

### Die nächsten Schritte

In dem Moment, in dem Sie Ihren Kundenauftrag "übertragen" haben, können Sie nun verschiedene Aktionen im Unternehmen anstossen:

* Um den Beschaffungsvorgang einzuleiten klicken Sie auf "Materialanforderung"
* Um den Versand einzuleiten klicken Sie auf "Auslieferung"
* Um eine Rechnung zu erstellen klicken Sie auf "Rechnung"
* Um den Prozess anzuhalten, klicken Sie auf "Anhalten"

### Übertragung

Der Kundenauftrag ist eine "übertragbare" Transaktion. Sehen Sie hierzu auch die Dokumentenphasen. Sie können abhängige Schritte (wie einen Lieferschein zu erstellen) erst dann durchführen, wenn Sie den Kundenauftrag übertragen haben.

### Kundenauftrag mit Wartungsauftrag

Wenn der Bestelltyp des Kundenauftrags "Wartung" ist, folgen Sie bitte unten dargestellten Schritten:

* **Schritt 1:** Geben Sie die Währung, die Preisliste und die Artikeldetails ein.
* **Schritt 2:** Berücksichtigen Sie Steuern und andere Informationen.
* **Schritt 3:** Speichern und übertragen Sie das Formular.
* **Schritt 4:** Wenn das Formular übertragen wurde, zeigt die Aktionsschaltfläche drei Auswahlmöglichkeiten: 1) Wartungsbesuch 2) Wartungsplan 3) Rechnung

> **Anmerkung 1:** Wenn Sie auf die Aktionsschaltfläche klicken und "Wartungsbesuch" auswählen können Sie das Besuchsformular direkt ausfüllen. Die Details werden automatisch aus dem Kundenauftrag übernommen.

> **Anmerkung 2:** Wenn Sie auf die Aktionsschaltfläche klicken und "Wartungsplan" auswählen, können Sie die Details zum Wartungsplan eintragen. Die Details werden autmomatisch aus dem Kundenauftrag übernommen.

> **Anmerkung 3:** Wenn Sie auf die Schaltfläche "Rechnung" klicken, können Sie eine Rechnung für die Wartungsarbeiten erstellen. Die Details werden automatisch aus dem Kundenauftrag übernommen.

{next}
