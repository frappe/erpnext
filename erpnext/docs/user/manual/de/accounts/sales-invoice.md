# Ausgangsrechung
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Eine Ausgangsrechnung ist eine Rechnung, die Sie an Ihren Kunden senden, und aufgrund derer der Kunde eine Zahlung leistet. Die Ausgangsrechnung ist ein Buchungsvorgang. Beim Übertragen einer Ausgangsrechnung aktualisiert das System das Forderungskonto und bucht einen Ertrag gegen das Kundenkonto.

Sie können eine Ausgangsrechnung direkt erstellen über:

> Rechnungswesen > Dokumente > Ausgangsrechnung > Neu

oder indem Sie in der rechten Ecke des Lieferscheins auf "Rechnung erstellen" klicken.

<img class="screenshot" alt="Ausgangsrechnung" src="/docs/assets/img/accounts/sales-invoice.png">

### Auswirkung auf die Buchhaltung

Alle Verkäufe müssen gegen ein Ertragskonto gebucht werden. Das bezieht sich auf ein Konto aus dem Abschnitt "Erträge" in Ihrem Kontenplan. Es hat sich als sinnvoll heraus gestellt, Erträge nach Ertragstyp (wie Erträge aus Produktverkäufen und Erträge aus Dienstleistungen) einzuteilen. Das Ertragskonto muss für jede Zeile der Postenliste angegeben werden.

> Tipp: Um Ertragskonten für Artikel voreinzustellen, können Sie unter dem Artikel oder der Artikelgruppe entsprechende Angaben eintragen.

Das andere Konto, das betroffen ist, ist das Konto des Kunden. Dieses wird automatisch über "Lastschrift für" im Kopfabschnitt angegeben.

Sie müssen auch die Kostenstelle angeben, auf die Ihr Ertrag gebucht wird. Erinnern Sie sich daran, dass Kostenstellen etwas über die Profitabilität verschiedener Geschäftsbereiche aussagen. Sie können in den Artikelstammdaten auch eine Standardkostenstelle eintragen.

### Buchungen in der doppelten Buchführung für einen typischen Verkaufsvorfall

So verbuchen Sie einen Verkauf aufgeschlüsselt:

**Soll:** Kunde (Gesamtsumme) 

**Haben:** Ertrag (Nettosumme, abzüglich Steuern für jeden Artikel) 

**Haben:** Steuern (Verbindlichkeiten gegenüber dem Staat)

> Um die Buchungen zu Ihrer Ausgangsrechnung nach dem Übertragen sehen zu können, klicken Sie auf Rechnungswesen > Hauptberichte > Hauptbuch.

### Termine

Veröffentlichungsdatum: Das Datum zu dem sich die Ausgangsrechnung auf Ihre Bilanz auswirkt, d. h. auf das Hauptbuch. Das wirkt sich auf alle Ihre Bilanzen in dieser Abrechnungsperiode aus.

Fälligkeitsdatum: Das Datum zu dem die Zahlung fällig ist (wenn Sie auf Rechnung verkauft haben). Das kann automatisch über die Kundenstammdaten vorgegeben werden.

### Wiederkehrende Rechnungen

Wenn Sie einen Vertrag mit einem Kunden haben, bei dem Sie dem Kunden monatlich, vierteljährlich, halbjährlich oder jährlich eine Rechnung stellen, dann können Sie das Feld "Wiederkehrende Rechnung" anklicken. Hier können Sie eingeben in welchen Abständen die Rechnungen erstellt werden sollen, und die Gesamtlaufzeit des Vertrages.

ERPNext erstellt dann automatisch neue Rechnungen und verschickt Sie an die angegebenen E-Mail-Adressen.

---

### Proforma-Rechnung

Wenn Sie einem Kunden eine Rechnung ausstellen wollen, damit dieser eine Anzahlung leisten kann, d. h. Sie haben Zahlung im Voraus vereinbart, dann sollten Sie ein Angebot erstellen und dieses als "Proforma-Rechnung" (oder ähnlich) bezeichnen, indem Sie die Funktion "Druckkopf" nutzen.

"Proforma" bezieht sich auf eine Formsache. Warum sollte man das tun? Wenn Sie eine Ausgangsrechnung buchen, dann erscheint diese bei den Forderungen und den Erträgen. Das ist genau dann nicht optimal, wenn nicht sicher ist, ob Ihr Kunden die Anzahlung auch wirklich leistet. Wenn Ihr Kunden aber dennoch eine "Rechnung" will, dann geben Sie ihm ein Angebot (in ERPNext) das als "Proforma-Rechnung" bezeichnet wird. Auf diese Weise ist jeder glücklich.

Das ist ein weithin gebräuchliches Verfahren. Wir bei Frappé machen das genauso.

{next}
