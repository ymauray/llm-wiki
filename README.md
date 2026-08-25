# 🧠 LLM Wiki - Knowledge Base Maintainer

Application Python basée sur le cahier des charges **LLM Wiki** d'[Andrej Karpathy](https://gist.githubusercontent.com/karpathy/442a6bf555914893e9891c11519de94f/raw/ac46de1ad27f92b28ac95459c782c07f6b8c964a/llm-wiki.md).

Au lieu d'effectuer du RAG classique (ré-extraction d'information depuis zéro à chaque requête), cette application **construit et maintient de manière incrémentale un wiki Markdown persistent** interconnecté qui synthétise au fur et me mesure vos documents sources.

---

## 🎯 Spécifications techniques respectées

1. **LiteLLM API**: Tous les appels aux modèles de langage sont gérés via la bibliothèque `litellm`.
2. **Nom de modèle strict**: Le modèle appelé est strictement nommé `"llm"`.
3. **Proxy LiteLLM & Clé d'API**: L'application lit `LITELLM_PROXY_API_BASE` et `LITELLM_PROXY_API_KEY` depuis les variables d'environnement (ou un fichier `.env`).
4. **Logique Karpathy**:
   - `/sources` : Répertoire contenant les documents bruts immuables (`.txt`, `.md`, `.docx` Word, `.pdf` PDF, etc.).
   - `/wiki` : Répertoire géré par le LLM (fiches d'entités, de concepts, résumés de sources, synthèses).
   - `wiki/index.md` : Catalogue orienté contenu mis à jour à chaque ingestion/synthèse.
   - `wiki/log.md` : Journal chronologique cumulatif au format exact `## [YYYY-MM-DD HH:MM] action | description`.
   - **Mise à jour incrémentale** : Détection des nouveaux fichiers ou fichiers modifiés sans tout réanalyser.

---

## 📁 Structure du Projet

```text
llm-wiki/
├── config.py             # Configuration, chemins et vérification des variables d'environnement
├── llm_client.py         # Module LiteLLM configuré strictement avec model="llm"
├── wiki_manager.py       # Logique métier (Ingestion, Index, Log, Query, Lint, Statuts)
├── cli.py                # Interface en ligne de commande et menu interactif
├── app.py                # Point d'entrée principal de l'application
├── web_app.py            # Serveur Web Flask et API REST
├── requirements.txt      # Liste des dépendances Python requises
├── .env.example          # Exemple de fichier de variables d'environnement
├── README.md             # Documentation et instructions d'exécution
├── AGENTS.md             # Document de transmission et contexte pour agents IA
├── static/               # Assets Web (CSS Glassmorphism, JavaScript)
├── templates/            # Gabarits HTML (Chat UI, Upload, Admin)
├── sources/              # Dossier où déposer vos documents bruts (.txt, .md, .docx, .pdf, etc.)
└── wiki/                 # Dossier structuré du Wiki persistant
    ├── entities/         # Fiches d'entités (Entite_*.md)
    ├── concepts/         # Fiches de concepts (Concept_*.md)
    ├── sources/          # Fiches de résumés de sources (Source_*.md)
    ├── syntheses/        # Fiches de synthèses thématiques (Synthesis_*.md)
    ├── index.md          # Catalogue général du wiki
    └── log.md            # Journal chronologique des opérations
```

---

## 🚀 Instructions d'installation et de lancement

### 1. Configuration des variables d'environnement

Définissez les variables d'environnement `LITELLM_PROXY_API_BASE` et `LITELLM_PROXY_API_KEY`.

Vous pouvez créer un fichier `.env` à la racine du projet :

```bash
cp .env.example .env
```

Puis éditez `.env` :

```env
LITELLM_PROXY_API_BASE=http://localhost:4000
LITELLM_PROXY_API_KEY=sk-1234567890abcdef
```

Ou directement dans votre terminal :

**Sur Linux / macOS :**
```bash
export LITELLM_PROXY_API_BASE="http://localhost:4000"
export LITELLM_PROXY_API_KEY="sk-1234567890abcdef"
```

**Sur Windows (PowerShell) :**
```powershell
$env:LITELLM_PROXY_API_BASE="http://localhost:4000"
$env:LITELLM_PROXY_API_KEY="sk-1234567890abcdef"
```

---

### 2. Installation des dépendances

Créez un environnement virtuel et installez les dépendances :

```bash
python -m venv venv
```

**Activation :**
- Linux / macOS : `source venv/bin/activate`
- Windows : `.\venv\Scripts\activate`

**Installation des packages :**
```bash
pip install -r requirements.txt
```

---

### 3. Utilisation de l'application

L'application propose une **Interface Web moderne (style ChatGPT / Gemini)** ainsi que des sous-commandes CLI.

#### A. Interface Web (Page principale, Téléversement, Administration)
Lancez simplement :
```bash
python app.py
# Ou explicitement :
python app.py web --port 5000
```
Ouvrez ensuite votre navigateur sur **http://localhost:5000** :
- **Page Principale (`/`)** : Interface de Chat / Requêtes similaire à Gemini / Claude. Posez des questions au wiki, prévisualisez les pages citées et enregistrez vos réponses sous forme de fiches de synthèse permanentes.
- **Page Téléversement (`/upload`)** : Zone de glisser-déposer pour téléverser vos documents (`.pdf`, `.docx`, `.txt`, `.md`, etc.) directement dans `/sources` et lancer l'ingestion incrémentale en un clic.
- **Page Administration (`/admin`)** : Tableau de bord des statistiques, explorateur de fiches wiki, suivi des logs `log.md`, bouton d'audit sémantique (Lint) et option de réinitialisation.

#### B. Mode sous-commandes CLI / Terminal
```bash
python app.py interactive   # Menu interactif dans le terminal
```

#### B. Mode sous-commandes CLI

- **Ingestion incrémentale** (traite les nouveaux fichiers dans `/sources`) :
  ```bash
  python app.py ingest
  ```

- **Poser une question au Wiki** :
  ```bash
  python app.py query "Quels sont les concepts clés présentés dans nos documents ?"
  ```
  *À la fin de la réponse, l'application vous proposera de sauvegarder la synthèse générée dans une nouvelle page persistent du wiki (`wiki/Synthesis_<nom>.md`).*

- **Audit et contrôle santé du Wiki (Lint)** :
  ```bash
  python app.py lint
  ```
  *Vérifie les liens cassés, les pages orphelines, les contradictions entre fiches et suggère des pistes d'amélioration.*

- **Afficher les statistiques et l'historique (Status)** :
  ```bash
  python app.py status
  ```

---

## ⚙️ Détails des opérations

1. **Ingest** :
   - Lit les documents de `/sources/`.
   - Utilise un manifest `.processed_sources.json` basé sur le hash des fichiers pour éviter de retraiter des documents non modifiés.
   - Demande au modèle `"llm"` via LiteLLM d'extraire les entités et concepts, de créer la fiche résumé de source (`Source_<nom>.md`) et de mettre à jour ou créer les fiches thématiques.
   - Reconstruit `wiki/index.md` par catégories.
   - Ajoute une entrée dans `wiki/log.md`.

2. **Query** :
   - Analyse l'index pour sélectionner les pages pertinentes.
   - Utilise le contexte des pages sélectionnées pour générer une réponse sourcée avec des liens internes Markdown `[Titre](Page.md)`.
   - Permet la réintégration de la réponse dans le wiki (savoir cumulatif).

3. **Lint** :
   - Analyse la cohérence structurelle (liens Markdown valide, recherche de pages orphelines).
   - Analyse la cohérence sémantique par le LLM (recherche de contradictions, données obsolètes, manques).
