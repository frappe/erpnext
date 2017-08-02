# Zahlungen durchführen
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Zahlungen zu Ausgangs- oder Eingangsrechnungen können über die Schaltfläche "Zahlungsbuchung erstellen" zu übertragenen Rechnungen erfasst werden.

  1. Aktualisieren Sie das Bankkonto (Sie können hier auch ein Standardkonto in den Unternehmensstammdaten einstellen).
  1. Aktualiseren Sie das Veröffentlichungsdatum.
  1. Geben Sie Schecknummer und Scheckdatum ein.
  1. Speichern und Übertragen Sie.

<img class="screenshot" alt="Zahlungen durchführen" src="/docs/assets/img/accounts/make-payment.png">

Zahlungen können auch unabhängig von Rechnungen erstellt werden, indem Sie einen neuen Journalbeleg erstellen und die Zahlungsart auswählen.

### Eingehende Zahlungen

Für Zahlungen von Kunden gilt:

* Soll: Bank oder Kasse
* Haben: Kundenkonto

> Anmerkung: Vergessen Sie nicht "Zu Ausgangsrechnung" und "Ist Anzahlung" zu markieren, wenn es zutrifft.

### Ausgehende Zahlungen

Für Zahlungen an Lieferanten gilt:

* Soll: Lieferant
* Haben: Bank oder Kasse

### Beispiel eines Buchungssatzes für eine Zahlung

<img class="screenshot" alt="Zahlungen durchführen" src="/docs/assets/img/accounts/new-bank-entry.png">

---

### Eine Zahlung per Scheck abgleichen

Wenn Sie Zahlungen per Scheck erhalten oder leisten, geben die Kontoauszüge Ihrer Bank nicht exakt die Daten Ihrer Buchung wieder, weil die Bank normalerweise einige Zeit braucht diese Zahlungen einzulösen. Das gleiche trifft zu, wenn Sie Ihrem Lieferanten einen Scheck zusenden und es einige Tage braucht, bis er vom Lieferanten angenommen und eingereicht wird. In ERPNext können Sie Kontoauszüge der Bank und Ihre Buchungssätze über das Werkzeug zum Kontenabgleich in Einklang bringen.

Dafür gehen Sie zu:

> Rechnungswesen > Werkzeuge > Kontenabgleich

Wählen Sie Ihr Bankkonto aus und geben Sie das Datum Ihres Kontoauszuges ein. Sie bekommen alle Buchungen vom Typ Bankbeleg. Aktualisieren Sie in jeder Buchung über die Spalte ganz rechts das "Einlösungsdatum" und klicken Sie auf "Aktualisieren".

So können Sie Ihre Kontoauszüge und Ihre Systembuchungen angleichen.

---

### Offene Zahlungen verwalten

Ausgenommen von Endkundenverkäufen sind in den meisten Fällen die Rechnungslegung und die Zahlung voneinander getrennte Aktivitäten. Es gibt verschiedene Kombinationsmöglichkeiten, wie Zahlungen getätigt werden können. Diese Kombinationen finden sowohl bei Verkäufen als auch bei Einkäufen Anwendung.

* Zahlungen können im Voraus erfolgen (100% Anzahlung).
* Sie können nach dem Versand erfolgen. Entweder zum Zeitpunkt der Lieferung oder innerhalb von ein paar Tagen.
* Es kann eine Teilzahlung im Voraus erfolgen und eine Restzahlung nach der Auslieferung.
* Zahlungen können zusammen für mehrere Rechnungen erfolgen.
* Anzahlungen können zusammen für mehrere Rechnungen erfolgen (und können dann auf die Rechnungen aufgeteilt werden).

ERPNext erlaubt es Ihnen alle diese Szenarien zu verwalten. Alle Buchungen des Hauptbuches können zu Ausgangsrechnungen, Eingangsrechnungen und Journalbelegen erfolgen.

Der gesamte offene Betrag einer Rechnung ist die Summe aller Buchungen, die zu dieser Rechnung erstellt wurden (oder mit ihr verknüpft sind). Auf diese Weise können Sie in Buchungssätzen Zahlungen kombinieren oder aufteilen um alle Szenarien abzudecken.

### Zahlungen mit Rechnungen abgleichen

In komplexen Szenarien, besonders im Geschäftsfeld Investitionsgüter, gibt es manchmal keinen direkten Bezug zwischen Zahlungen und Rechnungen. Sie schicken an Ihre Kunden Rechnungen und Kunden senden Ihnen Zahlungsblöcke oder Zahlungen, die auf einem Zeitplan basieren, der nicht mit Ihren Rechnungen verknüpft ist.

In solchen Fällen können Sie das Werkzeug zum Zahlungsabgleich verwenden.

> Rechnungswesen > Werkzeuge > Zahlungsabgleichs-Werkzeug

In diesem Werkzeug können Sie ein Konto auswählen (z. B. das Konto Ihres Kunden) und auf "Zahlungsbuchungen ermitteln" klicken und das System wählt alle offenen Journalbuchungen und Ausgangsrechnungen dieses Kunden aus.

Um Zahlungen und Rechnungen zu abzugleichen, wählen Sie Rechnungen und Journalbelege aus und klicken Sie auf "Abgleichen".

{next}
