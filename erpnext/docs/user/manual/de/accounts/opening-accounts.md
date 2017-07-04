# Eröffnungskonto
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Jetzt, da Sie den größten Teil der Einrichtung hinter sich haben, wird es Zeit tiefer einzusteigen!

Es gibt zwei wichtige Gruppen von Daten, die Sie eingeben müssen, bevor Sie Ihre Tätigkeiten beginnen.

* Die Stände in der Eröffnungsbilanz
* Die Anfangsbestände im Lager

Um Ihre Konten und Lagerbestände richtig eröffnen zu können, brauchen Sie belastbare Daten. Stellen Sie sicher, dass Sie Ihre Daten entsprechend vorbereitet haben.

### Konten eröffnen

Wir gehen davon aus, dass Sie mit der Buchhaltung in einem neuen Geschäftsjahr beginnen, Sie können aber auch mittendrin starten. Um Ihre Konten einzurichten, brauchen Sie Folgendes für den Tag an dem Sie die Buchhaltung über ERPNext starten.

* Eröffnungsstände der Kapitalkonten - wie Kapital von Anteilseignern (oder das des Inhabers), Darlehen, Stände von Bankkonten
* Liste der offenen Rechnungen aus Verkäufen und Einkäufen (Forderungen und Verbindlichkeiten)
* Entsprechende Belege

Sie können Konten basierend auf Belegarten auswählen. In so einem Szenario sollte Ihre Bilanz ausgeglichen sein.

<img class="screenshot" alt="Eröffnungskonto" src="{{docs_base_url}}/assets/img/accounts/opening-account-1.png">

Beachten Sie bitte auch, dass das System abstürzt, wenn es mehr als 300 Bücher gibt. Um so eine Situation zu vermeiden, können Sie Konten über temporäre Konten eröffnen.

### Temporäre Konten

Eine schöne Möglichkeit die Eröffnung zu vereinfachen bietet sich über die Verwendung von temporären Konten, nur für die Eröffnung. Die Kontenstände dieser Konten werden alle 0, wenn alle alten Rechnungen und die Eröffnungsstände von Bank, Schulden etc. eingegeben wurden. Im Standard-Kontenrahmen wird ein temporäres Eröffnungskonto unter den Vermögenswerten erstellt.

### Die Eröffnungsbuchung

In ERPNext werden Eröffnungskonten eingerichtet, indem bestimmte Buchungssätze übertragen werden.

Hinweis: Stellen Sie sicher, dass im Abschnitt "Weitere Informationen" "Ist Eröffnung" auf "Ja" eingestellt ist.

> Rechnungswesen > Journalbuchung > Neu

Vervollständigen Sie die Buchungssätze auf der Soll- und Haben-Seite.

<img class="screenshot" alt="Opening Account" src="{{docs_base_url}}/assets/img/accounts/opening-6.png">

Um einen Eröffnungsstand einzupflegen, erstellen Sie einen Buchungssatz für ein Konto oder eine Gruppe von Konten.

Beispiel: Wenn Sie die Kontenstände von drei Bankkonten einpflegen möchten, dann erstellen Sie Buchungssätze der folgenden Art und Weise:

<img class="screenshot" alt="Opening Account" src="{{docs_base_url}}/assets/img/accounts/opening-3.png">

Um einen Ausgleich herzustellen, wird ein temporäres Konto für Vermögen und Verbindlichkeiten verwendet. Wenn Sie einen Anfangsbestand in einem Verbindlichkeitenkonto einpflegen, können Sie zum Ausgleich ein temporäres Vermögenskonto verwenden.

Auf diese Art und Weise können Sie den Anfangsbestand auf Vermögens- und Verbindlichkeitenkonten erstellen.

Sie können zwei Eröffnungsbuchungssätze erstellen:

* Für alle Vermögenswerte (außer Forderungen): Dieser Buchungssatz beinhaltet alle Ihre Vermögenswerte außer den Summen, die Sie noch von Ihren Kunden als offene Forderungen zu Ihren Ausgangsrechnungen erhalten. Sie müssen Ihre Forderungen einpflegen, indem Sie zu jeder Rechnung eine individuelle Buchung erstellen (weil Ihnen das System dabei hilft, die Rechnungen, die noch bezahlt werden müssen, nachzuverfolgen). Sie können die Summe all dieser Forderungen auf der Habenseite zu einem **temporären Eröffnungskonto** buchen.
* Für alle Verbindlichkeiten: In ähnlicher Art und Weise müssen Sie einen Buchungssatz für die Anfangsstände Ihrer Verbindlichkeiten (mit Ausnahme der Rechnungen, die Sie noch zahlen müssen) zu einem **temporären Eröffnungskonto** erstellen.
* Mit dieser Methode können Sie Eröffnungsstände für spezielle Bilanzkonten einpflegen aber nicht für alle.
* Eine Eröffnungsbuchung ist nur für Bilanzkonten möglich, nicht aber für Aufwands- oder Ertragskonten.

Wenn Sie die Buchungen erstellt haben, schaut der Bericht zur Probebilanz in etwa wie folgt aus:

<img class="screenshot" alt="Probebilanz" src="{{docs_base_url}}/assets/img/accounts/opening-4.png">


### Offene Rechnungen

Nachdem Sie Ihre Eröffnungsbuchungen erstellt haben, müssen Sie alle Ausgangs- und Eingangsrechnungen, die noch offen sind, eingeben.

Da Sie die Erträge und Aufwendungen zu diesen Rechnungen bereits in der vorherigen Periode gebucht haben, wählen Sie in den Ertrags- und Aufwandskonten das **temporäre Eröffnungskonto** als Gegenkonto aus.

> Hinweis: Stellen Sie sicher, dass Sie jede Rechnung mit "Ist Eröffnungsbuchung" markiert haben.

Wenn es Ihnen egal ist, welche Artikel in diesen Rechnungen enthalten sind, dann erstellen Sie einfach einen Platzhalter-Artikel in der Rechnung. Die Artikelnummer ist in der Rechnung nicht zwingend erforderlich, also sollte das kein Problem sein.

Wenn Sie alle Ihre Rechnungen eingegeben haben, hat Ihr Eröffnungskonto einen Stand von 0.

{next}
