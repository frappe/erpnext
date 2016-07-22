# POS-Rechnung
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Der Point of Sale (POS) ist der Ort, wo ein Endkundengeschäft durchgeführt wird. Es handelt sich um den Ort, an dem ein Kunde im Austausch für Waren oder Dienstleistungen eine Zahlung an den Händler leistet. Für Endkundengeschäfte laufen die Lieferung von Waren, die Anbahnung des Verkaufs und die Zahlung alle am selben Ort ab, der im allgemeinen als "Point of Sale" bezeichnet wird.

Sie können eine Ausgangsrechnung des Typs POS erstellen, indem Sie "Ist POS" ankreuzen. Wenn Sie diese Option markieren, dann werden Sie bemerken, dass einige Felder verborgen werden und neue erscheinen.

> Tipp: Im Einzelhandel werden Sie wahrscheinlich nicht für jeden Kunden einen eigenen Datensatz anlegen. Sie können einen allgemeinen Kunden, den Sie als "Laufkunden" bezeichnen, erstellen und alle Ihre Transaktionen zu diesem Kundendatensatz erstellen.

#### POS einrichten

In ERPNext können über den POS alle Verkaufs- und Einkaufstransaktionen, wie Ausgangsrechnung, Angebot, Kundenauftrag, Lieferantenauftrag, usw. bearbeitet werden. Über folgende zwei Schritte richten Sie den POS ein:

1. Aktivieren Sie die POS-Ansicht über Einstellungen > Anpassen > Funktionseinstellungen
2. Erstellen Sie einen Datensatz für die [POS-Einstellungen]({{docs_base_url}}/user/manual/de/setting-up/pos-setting.html)

#### Auf die POS-Ansicht umschalten

Öffnen Sie eine beliebige Verkaufs- oder Einkaufstransaktion. Klicken Sie auf das Computersymbol <i class="icon-desktop"></i>.

#### Die verschiedenen Abschnitte des POS

* Lagerbestand aktualisieren: Wenn diese Option angekreuzt ist, werden im Lagerbuch Buchungen erstellt, wenn Sie eine Ausgangsrechnung übertragen. Somit brauchen Sie keinen separaten Lieferschein.
* Aktualisieren Sie in Ihrer Artikelliste die Lagerinformationen wie Lager (standardmäßig gespeichert), Seriennummer und Chargennummer, sofern sie zutreffen.
* Aktualisieren Sie die Zahlungsdetails wie das Bankkonto/die Kasse, den bezahlten Betrag etc.
* Wenn Sie einen bestimmten Betrag ausbuchen, zum Beispiel dann, wenn Sie zu viel gezahltes Geld erhalten, weil der Wechselkurs nicht genau umgerechnet wurde, dann markieren Sie das Feld "Offenen Betrag ausbuchen" und schließen Sie das Konto.

### Einen Artikel hinzufügen

An der Kasse muss der Verkäufer die Artikel, die der Kunde kauft, auswählen. In der POS-Schnittstelle können Sie einen Artikel auf zwei Arten auswählen. Zum einen, indem Sie auf das Bild des Artikels klicken, zum zweiten über den Barcode oder die Seriennummer.

**Artikel auswählen:** Um ein Produkt auszuwählen, klicken Sie auf das Bild des Artikels und legen Sie es in den Einkaufswagen. Ein Einkaufswagen ist ein Ort, der zur Vorbereitung der Zahlung durch den Kunden dient, indem Produktinformationen eingegeben, Steuern angepasst und Rabatte gewährt werden können.

**Barcode/Seriennummer:** Ein Barcode/eine Seriennummer ist eine optionale maschinenlesbare Möglichkeit Daten zu einem Objekt einzulesen, mit dem er/sie verbunden ist. Geben Sie wie auf dem Bild unten angegeben den Barcode/die Seriennummer in das Feld ein und warten Sie einen kurzen Moment, dann wird der Artikel automatisch zum Einkaufswagen hinzugefügt.

![POS]({{docs_base_url}}/assets/old_images/erpnext/pos-add-item.png)

> Tipp: Um die Menge eines Artikels zu ändern, geben Sie die gewünschte Menge im Feld "Menge" ein. Das wird hauptsächliche dann verwendet, wenn ein Artikel in größeren Mengen gekauft wird.

Wenn die Liste Ihrer Produkte sehr lang ist, verwenden Sie das Suchfeld und geben Sie dort den Produktnamen ein.

### Einen Artikel entfernen

Es gibt zwei Möglichkeiten einen Artikel zu entfernen:

* Wählen Sie einen Artikel aus, indem Sie auf die Zeile des Artikels im Einkaufswagen klicken. Klicken Sie dann auf die Schaltfläche "Löschen".
* Geben Sie für jeden Artikel, den Sie löschen möchten, als Menge "0" ein.

Wenn Sie mehrere verschiedene Artikel auf einmal entfernen möchten, wählen Sie mehrere Zeilen aus und klicken Sie auf die Schaltfläche "Löschen".

> Die Schaltfläche "Löschen" erscheint nur, wenn Artikel ausgewählt wurden.

![POS]({{docs_base_url}}/assets/old_images/erpnext/pos-remove-item.png)

### Zahlung durchführen

Wenn alle Artikel mit Mengenangabe im Einkaufswagen hinzugefügt wurden, können Sie die Zahlung durchführen. Der Zahlungsprozess untergliedert sich in drei Schritte:

1. Klicken Sie auf "Zahlung durchführen" um das Zahlungsfenster zu öffnen.
2. Wählen Sie die Zahlungsart aus.
3. Klicken Sie auf die Schaltfläche "Zahlen" um das Dokument abzuspeichern.

![POS-Zahlung]({{docs_base_url}}/assets/old_images/erpnext/pos-make-payment.png)

Übertragen Sie das Dokument um den Datensatz abzuschliessen. Nachdem das Dokument übertragen wurde, können Sie es entweder ausdrucken oder per E-Mail versenden.

#### Buchungssätze (Hauptbuch) für einen POS

Soll:

* Kunde (Gesamtsumme)
* Bank / Kasse (Zahlung)

Haben:

* Ertrag (Nettosumme abzüglich Steuern für jeden Artikel)
* Steuern (Verbindlichkeiten gegenüber dem Finanzamt)
* Kunde (Zahlung)
* Abschreibung/Ausbuchung (optional)

Um sich nach dem Übertragen die Buchungen anzusehen, klicken Sie auf Kontobuch ansehen.

{next}
