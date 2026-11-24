# Decisions: skill per il sync della documentazione pubblica

Reviewed: idea in conversazione (nuovo skill del plugin eng-skills) · Mode: interview · Updated: 2026-11-24

Sintesi: skill generico `docs-impact`, attivato prima della consegna (es. PR finale), che confronta le modifiche
del repo di lavoro con la documentazione pubblica, segnala impatti e adeguamenti richiesti e prepara un contesto
per una quick review. Unica specializzazione: GitHub Pages. Non fa la review né scrive la documentazione.

## Decided
- **Q1 Sorgente dei docs**: stesso repo di default, più una sorgente esterna dichiarabile in config (path locale o URL git). Copre il caso comune e quello dei docs separati.
- **Q2 Indice**: nessun DB persistente; scanner stateless Python stdlib (estrae termini dal diff, divide i docs in sezioni, match, ranking, report compatto). Benchmark: 3.000 file / 22 MB in 0,46 s; FTS5 non garantito su tutte le piattaforme e il collo di bottiglia è il contesto, non il tempo. Sostituisce il "piccolo db indicizzato" della richiesta iniziale; FTS5 resta possibile come cache opzionale se un eval lo dimostra necessario.
- **Q3 Rilevamento impatti**: estrazione automatica dei termini pubblici dal diff `base...HEAD` + mappatura dichiarata opzionale (glob codice → pagine). Zero config, ma cattura anche impatti senza termini in comune.
- **Q4 Output**: report impatti (sezione, causa, tipo di adeguamento: aggiornare / obsoleto / manca doc, confidenza) stampato e salvato nello scratchpad; si offre il passaggio a documentation-writer/reviewer, senza lanciarli.
- **Q5 Attivazione**: description dello skill + invocazione esplicita; nessun hook, nessun richiamo da altri skill per ora.
- **Q6 GitHub Pages**: rilevamento del metodo di pubblicazione + mappatura sorgente → URL nel report + controllo della navigazione (pagine nuove/rinominate assenti dal nav) + esclusione dell'output generato. Nessuna build.
- **Q7 Sorgente esterna**: path locale o URL git; clone shallow in cache `$(git rev-parse --git-common-dir)/docs-impact/`, aggiornato con fetch a ogni esecuzione.
- **D1 Nome**: `docs-impact`. *Default*
- **D2 Runtime script**: Python 3 solo stdlib, test unittest in `tests/`. *Default*
- **D3 Config**: estende la sezione `## Documentation` già letta da technical-writing. *Default*
- **D4 Base del diff**: branch base della PR, altrimenti default branch. *Default*
- **D5 Sola lettura**: lo skill non modifica mai i docs. *Default*
- **D6 Formati**: Markdown/MDX, reStructuredText, AsciiDoc, HTML solo per pagine sorgente. *Default*

## Discarded
- **Q1 Solo stesso repo / solo repo separato**: ciascuno esclude un caso reale.
- **Q2 SQLite FTS5**: FTS5 non garantito ovunque (due percorsi di codice), gestione staleness, nessun guadagno di velocità misurabile sui docs locali.
- **Q2 JSON persistente**: staleness senza beneficio.
- **Q2 Solo Grep dell'agente**: output grezzo nel contesto, niente sezioni né ranking.
- **Q3 Solo estrazione / solo mappatura**: la prima perde gli impatti descritti a parole, la seconda richiede config.
- **Q4 Lancio diretto del reviewer / commento PR**: oltre il perimetro dello skill.
- **Q5 Hook prima di gh pr create**: scatterebbe per tutti gli utenti del plugin su ogni PR.
- **Q6 Build locale del sito**: richiede toolchain del generatore, contro la genericità.
- **Q6 Solo rilevamento**: non vede URL e navigazione, gli impatti specifici di Pages.
- **Q7 Solo path locale**: non funziona in CI né su macchina nuova senza passi manuali.
