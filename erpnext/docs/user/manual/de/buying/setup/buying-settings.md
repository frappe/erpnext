# Einstellungen zum Einkauf
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Hier können Sie Werte einstellen, die in den Transaktionen des Moduls Einkauf zugrunde gelegt werden.

![Einkaufseinstellungen]({{docs_base_url}}/assets/img/buying/buying-settings.png)

Lassen Sie uns die verschiedenen Optionen durckgehen.

### 1. Bezeichnung des Lieferanten nach

Wenn ein Lieferant abgespeichert wird, erstellt das System eine eindeutige Kennung bzw. einen eindeutigen Namen für diesen Lieferanten, auf den in verschiedenen Einkaufstransaktionen Bezug genommen wird.

Wenn nicht anders eingestellt, verwendet ERPNext den Lieferantennamen als eindeutige Kennung. Wenn Sie Lieferanten nach Namen wir SUPP-00001, SUP-00002 unterscheiden wollen, oder nach Serien eines bestimmten Musters, stellen Sie die Benahmung der Lieferanten auf "Nummernkreis" ein.

Sie können den Nummernkreis selbst definieren oder einstellen:

> Einstellungen > Einstellungen > Nummernkreis

[Klicken Sie hier, wenn Sie mehr über Nummernkreise wissen möchten]({{docs_base_url}}/user/manual/de/setting-up/settings/naming-series.html)

### 2. Standard-Lieferantentyp

Stellen Sie hier ein, was der Standartwert für den Lieferantentyp ist, wenn ein neuer Lieferant angelegt wird.

### 3. Standard-Einkaufspreisliste

Geben Sie an, was der Standardwert für die Einkaufspreisliste ist, wenn eine neue Einkaufstransaktion erstellt wird.

### 4. Selben Preis während des gesamten Einkaufszyklus beibeihalten

Wenn diese Option aktiviert ist, wird Sie ERPNext unterbrechen, wenn Sie den Artikelpreis in einer Lieferantenbestellung oder in einem auf einer Lieferantenbestellung basierenden Kaufbeleg ändern wollen, d. h. das System behält den selben Preis während des gesamten Einkaufszyklus bei. Wenn Sie den Artikelpreis unbedingt ändern müssen, sollten Sie diese Option deaktivieren.

### 5. Lieferantenbestellung benötigt

Wenn diese Option auf "JA" eingestellt ist, hält Sie ERPNext davon ab, eine Eingangsrechnung oder einen Kaufbeleg zu erstellen ohne vorher einen Lieferantenauftrag erstellt zu haben.

### 6. Kaufbeleg benötigt

Wenn diese Option aUf "JA" eingestellt ist, hält Sie ERPNext davon ab, eine Eingangsrechnung zu erstelln, ohne vorher einen Kaufbeleg erstellt zu haben.

{next}
