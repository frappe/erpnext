# Kontenabgleich
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

### Kontoauszug

Ein Kontenabgleich ist ein Prozess, welcher den Unterschied zwischen dem Kontostand, der auf dem Kontoauszug einer Organisation wie von der Bank angegeben erscheint, und dem zugehörigen Betrag, wie er in den eigenen Buchhaltungsuntertalgen der Organisation zu einem bestimmten Zeitpunkt erscheint, aufklärt.

Solche Unterschiede können zum Beispiel dann auftauchen, wenn ein Scheck oder eine Menge an Schecks, die von der Organisation ausgeschrieben wurden, nicht bei der Bank eingereicht wurden, wenn eine Banküberweisung, wie zum Beispiel eine Gutschrift, oder eine Bankgebühr noch nicht in den Buchhaltungsdaten der Organisation erfasst wurden, oder wenn die Bank oder die Organisation selbst einen Fehler gemacht haben.

Der Kontoauszug erscheint in ERPNext in der Form eines Berichtes.

#### Abbilung 1: Kontoauszug

![]({{docs_base_url}}/assets/old_images/erpnext/bank-reconciliation-2.png) 

Wenn Sie den Bericht erhalten, überprüfen Sie bitte, ob das Feld "Abwicklungsdatum" wie bei der Bank angegeben mit dem Kontoauszug übereinstimmt. Wenn die Beträge übereinstimmen, dann werden die Abwicklungsdaten abgeglichen. Wenn die Beträge nicht übereinstimmen, dann überprüfen Sie bitte die Abwicklungsdaten und die Journalbuchungen/Buchungssätze.

Um Abwicklungsbuchungen hinzuzufügen, gehen Sie zu Rechnungswesen > Werkzeuge > Kontenabgleich.

### Werkzeug zum Kontenabgleich

Das Werkzeug zum Kontenabgleich in ERPNext hilft Ihnen dabei Abwicklungsdaten zu den Kontoauszügen hinzuzufügen. Um eine Scheckzahlung abzugleichen gehen Sie zum Punkt "Rechnungswesen" und klicken Sie auf "Kontenabgleich".

**Schritt 1:** Wählen Sie das Bankkonto aus, zu dem Sie abgleichen wollen. Zum Beispiel: Deutsche Bank, Sparkasse, Volksbank usw.

**Schritt 2:** Wählen Sie den Zeitraum aus, zu dem Sie abgleichen wollen.

**Schritt 3:** Klicken Sie auf "Abgeglichene Buchungen mit einbeziehen".

Jetzt werden alle Buchungen im angegebenen Zeitraum in der Tabelle darunter angezeigt.

**Schritt 4:** Klicken Sie auf den Journalbeleg in der Tabelle und aktualisieren Sie das Abwicklungsdatum.

#### Abbildung 2: Werkzeug zum Kontenabgleich

<img class="screenshot" alt="Kontenabgleich" src="{{docs_base_url}}/assets/img/accounts/bank-reconciliation.png">

**Schritt 5:** Klicken Sie auf die Schaltfläche "Abwicklungsdatum aktualisieren"

{next}
