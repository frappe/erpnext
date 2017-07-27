# Nummernkreis
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

### 1. Einleitung

Datensätze werden ganz allgemein nach "Stammdaten" oder "Transaktionen" eingeteilt. Ein Stammdatensatz ist ein Datensatz der einen "Namen" hat, z. B. von einem Kunden, einem Artikel, einem Lieferanten, einem Mitarbeiter, etc. Eine Transaktion hat demgegenüber eine "Nummer". Beispiele für Transaktionen sind Ausgangsrechnung, Angebot usw. Sie erstellen Transaktionen zu einer Anzahl von Stammdatensätzen.

ERPNext erlaubt es Ihnen, Ihren Transaktionen Präfixe voranzustellen, wobei jedes Präfix einen eigenen Nummernkreis darstellt. So hat z. B. der Nummernkreis INV12 die Nummern INV120001, INV120002 usw.

Sie können für all Ihre Transaktionen viele verschiedene Nummernkreise verwenden. Gewöhnlicherweise wird für jedes Geschäftsjahr ein eigener Nummernkreis verwendet. In Ausgangsrechnungen können Sie z. B. folgende verwenden:

* INV120001
* INV120002
* INV-A-120002

usw. Sie können auch für jeden Kundentyp oder für jedes Ihrer Einzelhandelsgeschäfte einen eigenen Nummernkreis verwenden.

### 2. Verwalten von Nummernkreisen für Dokumente

Um einen Nummernkreis einzustellen, gehen Sie zu:

> Einstellungen > Daten > Nummernkreis

In diesem Formular,

1. Wählen Sie die Transaktion aus, für die Sie den Nummernkreis einstellen wollen. Das System wird den aktuellen Nummernkreis in der Textbox aktualisieren.
2. Passen Sie den Nummernkreis nach Ihren Wünschen mit eindeutigen Präfixen an. Jedes Präfix muss in einer neuen Zeile stehen.
3. Das erste Präfix wird zum Standard-Präfix. Wenn Sie möchten, dass ein Benutzer explizit einen Nummernkreis statt der Standardeinstellung auswählt, markieren Sie die Option "Benutzer muss immer auswählen".

Sie können auch den Startpunkt eines Nummernkreises auswählen, indem Sie den Namen und den Startpunkt des Nummernkreises im Abschnitt "Seriennummer aktualisieren" angeben.

### 3. Beispiel

Sehen Sie hier, wie der Nummernkreis eingestellt wird.

<img class="screenshot" alt="Nummernkreise" src="{{docs_base_url}}/assets/img/setup/settings/naming-series.gif">

{next}
