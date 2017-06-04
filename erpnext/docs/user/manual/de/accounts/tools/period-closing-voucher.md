# Periodenabschlussbeleg
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Zum Ende eines jeden Jahres (oder evtl. auch vierteljährlich oder monatlich) und nachdem Sie die Bücher geprüft haben, können Sie Ihre Kontenbücher abschliessen. Das heißt, dass Sie die besonderen Abschlussbuchungen durchführen können, z. B.:

* Abschreibungen
* Wertveränderungen des Anlagevermögens
* Rückstellungen für Steuern und Verbindlichkeiten
* Aktualisieren von uneinbringbaren Forderungen

usw. und Sie können Ihren Gewinn oder Verlust verbuchen.

Wenn Sie das tun, muss der Kontostand Ihres GuV-Kontos 0 werden. Sie starten ein neues Geschäftsjahr (oder eine Periode) mit einer ausgeglichenen Bilanz und einem jungfräulichen GuV-Konto.

Sie sollten nach den Sonderbuchungen zum aktuellen Geschäftsjahr über Journalbuchungen in ERPNext alle Ihre Ertrags- und Aufwandskonten auf 0 setzen, indem Sie hierhin gehen:

> Buchhaltung > Werkzeuge > Periodenabschlussbeleg

Das **Buchungsdatum** ist das Datum, zu dem die Buchung ausgeführt wird. Wenn Ihr Geschäftsjahr am 31. Dezember endet, dann sollten Sie dieses Datum als Buchungsdatum im Periodenabschlussbeleg auswählen.

Das **Transaktionsdatum** ist das Datum, zu dem der Periodenabschlussbeleg erstellt wird.

Das **abzuschließende Geschäftsjahr** ist das Jahr, für das Sie Ihre Finanzbuchhaltung abschliessen.

<img class="screenshot" alt="Periodenabschlussbeleg" src="{{docs_base_url}}/assets/img/accounts/period-closing-voucher.png">

Dieser Beleg überträgt den Gewinn oder Verlust (über die GuV ermittelt) in die Schlußbilanz. Sie sollten ein Konto vom Typ Verbindlichkeiten, wie Gewinnrücklagen oder Überschuss, oder vom Typ Kapital als Schlußkonto auswählen.

Der Periodenabschlussbeleg erstellt Buchungen im Hauptbuch, bei denen alle Ertrags- und Aufwandskonten auf 0 gesetzt werden, und überträgt den Gewinn oder Verlust in die Schlußbilanz.

Wenn Sie Buchungen zu einem abgeschlossenen Geschäftsjahr erstellen, besonders dann, wenn für dieses Geschäftsjahr schon ein Periodenabschlussbeleg erstellt wurde, sollten Sie einen neuen Periodenabschlussbeleg erstellen. Der spätere Beleg überträgt dann nur den offenen Differenzbetrag aus der GuV in die Schlußbilanz.

{next}
