# Register and wording, in English and Italian

Write in the document's language, taken from the project's `## Documentation` section or from the document you are
editing. Code identifiers, commands, flags, configuration keys and UI labels stay exactly as they are in every
language.

## Formality by reader and channel

| Reader | Published docs, UI, help | Email | Chat |
|---|---|---|---|
| Product users, customers | Direct, neutral | Formal | Neutral |
| Partner, client, supplier, other company | Direct, neutral | Formal | Neutral or formal, as they write |
| Colleague in another team | n/a | Neutral | Informal |
| Own team | n/a | Informal | Informal |

Mirror the register of an existing thread unless it is less formal than the table allows for that reader.

## Both languages

- One term per concept, the same as in the UI and the API names; follow the project glossary when there is one.
- Active voice, present tense, short sentences; the subject is whoever acts.
- No marketing words ("seamless", "powerful", "robust"; "potente", "innovativo", "all'avanguardia") and no
  "simply", "just", "basta", "semplicemente": they tell the reader the task is easy when it may not be for them.
- No filler openings ("I hope this finds you well", "Spero tu stia bene", "Come anticipato") in front of the
  bottom line.
- Numbers as digits with their unit; dates written out or unambiguous for the reader (`12 March 2027`,
  `12/03/2027` only for Italian readers).

## English

- Docs and UI: second person ("you"), imperative for steps.
- Formal email: "Dear Ms Okafor," … "Kind regards,". Neutral: "Hello Ana," … "Best regards,". Informal: "Hi Ana,"
  and no closing formula in chat.

## Italian

- **Form of address**: a project setting (`Register (IT)` in `## Documentation`). When it is not set:
  - docs, UI and help: **tu** ("Apri **Impostazioni**", "Puoi esportare…");
  - formal email to a person: **Lei**, with the capital in pronouns and possessives ("Le invio", "la Sua
    richiesta"); to a company or a team: **voi**;
  - colleagues: **tu**.
  Never mix forms in one text.
- **Impersonal forms** ("si consiglia di", "è necessario") only where no reader acts; a step is an imperative.
- **Anglicisms**: keep established technical terms in English (*commit*, *deploy*, *repository*, *build*,
  *webhook*, *token*), in roman type, invariable in the plural ("i commit", "due webhook"). Use the Italian word when
  a common one exists (*impostazioni*, not *settings*; *scaricare*, not *downloadare*; *pianificare*, not
  *schedulare*). Gender of an English noun follows the Italian equivalent ("la pipeline", "il branch").
- **Typography**: decimal comma in prose ("1,5 GB"), unchanged inside code; dates "12 marzo 2027" or "12/03/2027";
  "e-mail" or "email", one form per document; accented capitals as letters ("È", not "E'").
- **Salutations**: formal "Gentile dott.ssa Ferri," or "Gentile Mario Rossi," … "Cordiali saluti,"; to a company
  "Spettabile Alfa S.r.l.," only in letters; neutral "Buongiorno Mario," … "Un saluto,"; informal "Ciao Mario," and
  no closing formula in chat.
- **Bottom line first in Italian too**: the request goes in the first sentence after the salutation ("Le chiedo di
  approvare … entro il 12 marzo."), not after "Le scrivo per…" and a paragraph of background.
