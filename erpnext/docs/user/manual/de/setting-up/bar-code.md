# Barcode
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Ein Barcode ist ein maschinenlesbarer Code und besteht aus Nummern und Mustern von parallelen Linien mit unterschiedlicher Breite, die auf eine Ware aufgedruckt werden. Barcodes werden speziell zur Lagerverwaltung verwendet.

Wenn Sie einen Artikel bei einem beliebigen Geschäft kaufen, dann werden Sie einen Aufkleber mit dünnen Linien erkennen, versehen mit einer Kombination von verschiedenen Zahlen. Dieser Aufkleber wird dann vom Kassierer eingescannt und die Beschreibung und der Preis werden automatisch übernommen. Diese Anordnung von Linien und Zahlen bezeichnet man als Barcode.

Ein Barcode-Lesegerät liest die Nummer des Aufklebers eines Artikels ein. Um mit ERPNext Barcodes zu nutzen, verbinden Sie den Barcodeleser mit Ihrer Hardware. Gehen Sie dann zu den ERPNext-Einstellungen und aktivieren Sie "Barcode" indem Sie zu den Werkzeugen gehen und auf die Funktion "verbergen / anzeigen" klicken. Kreuzen Sie dann das Feld "Artikel-Barcode" an.

> Einstellungen > Anpassen > Funktionen einstellen > Artikelbarcode

### Abbildung 1: Markieren Sie das Feld "Artikelbarcode"

<img class="screenshot" alt="Barcode" src="/docs/assets/img/setup/barcode-1.png">

Wenn Sie einen Barcode einlesen wollen, gehen Sie zu:

> Rechnungswesen > Dokumente > Eingangsrechnung

Klicken Sie unter dem Artikel auf "Neue Zeile einfügen". Die Artikelzeile erweitert sich um neue Felder anzuzeigen. Positionieren Sie Ihre Schreibmarke im Barcodefeld und beginnen Sie mit dem Einlesen. Der Barcode wird im entsprechenden Feld aktualisiert. Nachdem der Barcode eingelesen wurd, holt das System automatisch alle Artikeldetails aus dem System.

Aktivieren Sie der Einfachheit halber die POS-Ansicht in ERPNext. Der Aktivierungsprozess ist der selbe wie bei der Barcodeaktivierung. Gehen Sie in die Einstellungen und klicken Sie auf "Funktionen einstellen". Aktivieren Sie dann das Feld "Ist POS".

Gehen Sie dann zu "Rechnungswesen" und klicken Sie auf Ausgangsrechnung. Aktivieren Sie das Feld "Ist POS".

### Abbildung 2: Aktivieren Sie das Feld "Ist POS"

<img class="screenshot" alt="Barcode" src="/docs/assets/img/setup/barcode-2.png">

Gehen Sie zu "Artikel" und klicken Sie auf "Neue Zeile einfügen".

Die Schreibmarke wird automatisch im Barcodefeld positioniert. So können Sie sofort den Barcode einlesen und mit Ihren Arbeiten fortfahren.

{next}
