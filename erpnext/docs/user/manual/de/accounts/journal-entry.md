# Journalbuchung / Buchungssatz
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Außer der **Ausgangsrechnung** und der **Eingangsrechnung** werden alle Buchungsvorgänge als **Journalbuchung / Buchungssatz** erstellt. Ein **Buchungssatz** ist ein Standard-Geschäftsvorfall aus dem Rechnungswesen, der sich auf mehrere verschiedene Konten auswirkt und bei dem die Summen von Soll und Haben gleich groß sind.

Um einen neuen Buchungssatz zu erstellen, gehen Sie zu:

> Rechnungswesen > Dokumente > Journalbuchung > Neu

<img class="screenshot" alt="Buchungssatz" src="{{docs_base_url}}/assets/img/accounts/journal-entry.png">

In einem Buchungssatz müssen Sie folgendes tun:

* Die Belegart über das DropDown-Menü auswählen.
* Zeilen für die einzelnen Buchungen hinzufügen. In jeder Zeile müssen Sie folgendes Angeben:
    * Das Konto, das betroffen ist.
    * Die Beträge für Soll und Haben.
    * Die Kostenstelle (wenn es sich um einen Ertrag oder einen Aufwand handelt)
    * Den Gegenbeleg: Verknüpfen Sie hier mit einem Beleg, oder einer Rechnung, wenn es sich um den "offenen" Betrag dieser Rechnung handelt.
    * Ist Anzahlung: Wählen Sie hier "Ja" wenn Sie diese Option in einer Rechnung auswählen können möchten. Oder geben Sie andere Informationen an, wenn es sich um "Bankzahlung" oder "auf Rechnung" handelt.

#### Differenz

Das "Differenz"-Feld zeigt den Unterschied zwischen den Soll- und Habenbeträgen. Dieser Wert sollte "0" sein bevor der Buchungssatz übertragen wird. Wenn dieser Wert nicht "0" ist, dann können Sie auf die Schaltfläche "Differenzbuchung erstellen" klicken, um eine neue Zeile mit dem benötigten Betrag, der benötigt wird, die Differenz auf "0" zu stellen, einzufügen.

---

### Standardbuchungen

Schauen wir uns einige Standardbuchungssätze an, die über Journalbelege erstellt werden können.

#### Aufwände (nicht aufgeschlüsselt)

Oftmals ist es nicht notwendig einen Aufwand genau aufzuschlüsseln, sondern er kann bei Zahlung direkt auf ein Aufwandskonto gebucht werden. Beispiele hierfür sind eine Reisekostenabrechnung oder eine Telefonrechnung. Sie können Aufwände für Telefon direkt verbuchen anstatt mit dem Konto Ihres Telekommunikationsanbieters und die Zahlung auf dem Bankkonto belasten.

* Soll: Aufwandskonto (wie Telefon)
* Haben: Bank oder Kasse

#### Zweifelhafte Forderungen und Abschreibungen

Wenn Sie eine Rechnung als uneinbringbar abschreiben wollen, können Sie einen Journalbeleg ähnlich einem Zahlungsbeleg erstellen, nur dass Sie nicht Ihre Bank belasten, sondern das Aufwandskonto "Uneinbringbare Forderungen".

* Soll: Abschreibungen auf uneinbringbare Forderungen
* Haben: Kunde

> Anmerkung: Beachten Sie, dass es spezielle landesspezifische Regeln für das Abschreiben uneinbringbarer Forderungen gibt.

#### Abschreibungen aufgrund von Wertminderungen

Eine Abschreibung tritt dann auf, wenn Sie einen bestimmten Wert Ihres Vermögens als Aufwand abschreiben. Beispielsweise einen Computer, den Sie auf fünf Jahre nutzen. Sie können seinen Wert über die Periode verteilen und am Ende jeden Jahres einen Buchungssatz erstellen, der seinen Wert um einen bestimmten Prozentsatz vermindert.

* Soll: Abschreibung (Aufwand)
* Haben: Vermögenskonto (das Konto auf das Sie den Vermögenswert, denn Sie abschreiben, gebucht haben)

> Anmerkung: Beachten Sie, dass es spezielle landesspezifische Regeln dafür gibt, in welcher Höhe bestimmte Arten von Vermögensgegenständen abgeschrieben werden können.

{next}
