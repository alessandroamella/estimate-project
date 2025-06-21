# Cos'è

È un semplice script che genera un preventivo per un progetto in base a un file markdown.

# Esempio: preventivo-libri.md

## Preventivo Backend – Sistema di Prestito Libri (MVP)

Stima per lo sviluppo dei servizi backend di un'applicazione minimale per il prestito di libri.

**Stack Tecnologico**: TypeScript, Express.js, PostgreSQL, Prisma ORM

---

### Setup Backend & Database

- Setup del progetto Express
- Configurazione PostgreSQL e Prisma
- Definizione tabelle: `Users`, `Books`, `Loans`
- Script di seeding con utenti e libri di test

**Stima ore**: 10–15 ore

---

### Autenticazione e Gestione Utenti

- Autenticazione JWT base: registrazione e login
- Ruoli: `admin`, `membro`
- Endpoint: profilo utente, elenco libri presi in prestito

**Stima ore**: 8–10 ore

---

### Logica di Prestito Libri

- Endpoint: presta libro (verifica disponibilità)
- Endpoint: restituisci libro
- Validazioni: massimo 3 libri per utente

**Stima ore**: 8–12 ore

---

### Funzionalità Admin

- Elenco prestiti scaduti
- Aggiunta/modifica/rimozione libri
- Visualizzazione utenti attivi

**Stima ore**: 6–8 ore

---

# Output

### Riepilogo stime

| Fase                             | Ore Min | Ore Max |
| :------------------------------- | :-----: | :-----: |
| Setup Backend & Database         |   10    |   15    |
| Autenticazione e Gestione Utenti |    8    |   10    |
| Logica di Prestito Libri         |    8    |   12    |
| Funzionalità Admin               |    6    |    8    |
| **TOTALE**                       | **32**  | **45**  |

### Stima economica

**Range di prezzo: €1.090 - €1.620**

### Timeline stimata

**2-4 settimane** per il completamento.

---

# Uso

```bash
python stima.py preventivo-libri.md
```
