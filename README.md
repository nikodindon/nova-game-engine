# Nova Game Engine

**Générateur de jeux Python + Pygame depuis un prompt en langage naturel.**
100% local —LLMs locaux uniquement, zéro cloud.

Le moteur analyse une demande en langage naturel, produit une spécification détaillée, génère le code Python, le vérifie, et le corrige automatiquement. Résultat : un jeu jouable en quelques minutes.

---

## Principe

```
Prompt → Architect → SPEC.md (détaillée, vérifiable)
                   ↓
              Coder → fichiers .py (complets, syntaxiquement valides)
                   ↓
              Critic → check list feature par feature
                   ↓
         [boucle fix × 3 si nécessaire]
                   ↓
                Joue !
```

Chaque agent est un LLM dédié. Les prompts sont pensés pour des modèles de 3B+ sur CPU.

---

## Installation

```bash
git clone https://github.com/nikodindon/nova-game-engine.git
cd nova-game-engine
pip install -r requirements.txt
```

**Dépendances :** `pygame`, `numpy`.

---

## LLM local — Setup

Le moteur exige un serveur LLM local. Tous les modèles GGUF fonctionnent.

### Lance un serveur (exemple avec Qwen 3B sur port 8082)

```bash
llama-server \
  -m ~/llm_models/qwen-3b/Qwen2.5-Coder-3B-Instruct-Q6_K.gguf \
  -c 8192 \
  -tb 12 \
  -ngl 0 \
  --port 8082
```

### Configure

Édite `config.json` :

```json
{
  "provider": "llama-server",
  "model": "Qwen2.5-Coder-3B-Instruct-Q6_K",
  "base_url": "http://localhost:8082",
  "timeout": 300,
  "temperature": 0.1,
  "max_out_tokens": 4096
}
```

---

## Utilisation

```bash
# Génère et lance automatiquement
python main.py "Space Invaders minimal avec son"

# Génère sans lancer (analyse les fichiers)
python main.py --no-play "Breakout avec power-ups"

# Mode debug — log complet de tous les prompts/responses
python main.py --debug "Pong à deux joueurs"

# Avec un nom de session
python main.py --session tetris "Tetris avec niveaux de difficulté"

# Lister les sessions passées
python main.py --list

# Rejouer une session existante
python main.py --play ma_session_20250425_143022
```

---

## Modèles recommandés

| Agent | Modèle | Pourquoi |
|-------|--------|----------|
| **Architect** | Qwen2.5-Coder 7B ou Llama3 8B | Raisonnement architectural, specs bien structurées |
| **Coder** | Qwen2.5-Coder 3B minimum | Spécifique Python, imports corrects |
| **Critic** | Qwen2.5-Coder 3B+ | Contexte long pour analyser plusieurs fichiers |
| **Planner** | N'importe quel 3B+ | JSON borné, prompt court |

Le 1.5B produit des specs vagues et du code corrompu. Utiliser pour des tâches triviales uniquement.

### Modèles déjà téléchargés

```
~/llm_models/qwen-1.5b/Qwen2.5-Coder-1.5B-Instruct-Q8_0.gguf   (1.6Go) → :8081
~/llm_models/qwen-3b/Qwen2.5-Coder-3B-Instruct-Q6_K.gguf       (2.4Go) → :8082
~/llm_models/qwen-7b/Qwen2.5-Coder-7B-Instruct-Q5_K_M.gguf     (5.1Go) → pret
```

```bash
# Qwen 3B sur port 8082
llama-server -m ~/llm_models/qwen-3b/Qwen2.5-Coder-3B-Instruct-Q6_K.gguf \
  -c 8192 -tb 12 -ngl 0 --port 8082

# Qwen 7B sur port 8083
llama-server -m ~/llm_models/qwen-7b/Qwen2.5-Coder-7B-Instruct-Q5_K_M.gguf \
  -c 8192 -tb 12 -ngl 0 --port 8083
```

---

## Architecture du projet

```
nova-game-engine/
├── main.py              # CLI + boucle principale + DebugLogger
├── config.json          # Config LLM (provider, modèle, URL)
├── requirements.txt
├── README.md
├── core/
│   ├── config.py        # Chargement config JSON avec defaults
│   └── llm.py           # Client HTTP → llama-server (API OpenAI compat)
└── agent/
    ├── architect.py     # Prompt → SPEC.md structurée
    ├── coder.py         # SPEC.md → fichiers .py (blocs code Python)
    ├── critic.py        # Vérification feature par feature
    ├── planner.py       # Critic output → plan de fix JSON
    ├── prompts.py       # System prompts (_ARCHITECT, _CODER, _CRITIC, _PLANNER)
    └── session.py       # Gestion dossier session + résultats
```

---

## Sessions

Chaque session génère un dossier dans `~/nova-game-engine/sessions/<name>/` :

```
<session>/
├── SPEC.md          # Spécification originale
├── result.txt       # Verdict + review du Critic
├── debug.log        # Log complet JSON Lines (--debug)
└── game/            # Fichiers Python du jeu
    ├── main.py
    ├── constants.py
    ├── entities.py
    └── sound_manager.py
```

### Format du debug.log

Chaque ligne = événement JSON horodaté :

```json
{"ts": "2026-04-25T15:30:01.123", "event": "LLM_REQ", "step": "ARCHITECT", "data": {"agent": "architect", "model": "...", "prompt_len": 1234}}
{"ts": "2026-04-25T15:30:45.567", "event": "LLM_RESP", "step": "ARCHITECT", "data": {"agent": "architect", "response_len": 5678, "duration_s": 45.2}}
{"ts": "2026-04-25T15:31:02.890", "event": "FILE_GENERATED", "step": "CODER", "data": {"filename": "main.py", "size_bytes": 2345}}
{"ts": "2026-04-25T15:31:30.001", "event": "VERDICT", "step": "CRITIC", "data": {"verdict": "ALL_COMPLETE", "review": "..."}}
```

---

## Pipeline — détailagent paragent

### 1. Architect

Reçoit le prompt utilisateur. Produce a `SPEC.md` avec :

```
# Project: <nom>
## Fichiers
- `main.py` — ... (rôle précis)
- `constants.py` — ... (rôle précis)
...
## Fonctionnalités
1. <feature observable> — detail concret
2. <feature observable> — detail concret
...
## Rendu
<description visuelle>
## Controles
<liste des controles>
## Contraintes techniques
- Python 3 + pygame
- Son procedural (numpy)
...
```

**Règle :** chaque feature doit être vérifiable par le Critic (observable dans le code, pas une intention).

### 2. Coder

Reçoit la SPEC.md. Génère chaque fichier comme un bloc Markdown `` ```python ... ``` ``.

**Parsing :** cherche le premier bloc ` ```python ` et le dernier ` ``` ` dans la réponse. Plus robuste que les tool calls `<tool>` qui échouent silencieusement.

**Règle :** code complet, zéro placeholder, zéro TODO. Si le LLM hésite sur une feature, il laimplémente quand même de façon simple.

### 3. Critic

Reçoit SPEC.md + tous les fichiers générés. Check chaque feature :

```
FEATURE 1: [✓/✗] Description — fichier:lineno ou MISSING
FEATURE 2: [✓/✗] Description — fichier:lineno ou MISSING
...

VERDICT: ALL_COMPLETE
```
ou
```
VERDICT: NEEDS_FIXES
Top 3:
1. [fichier] — reason
2. [fichier] — reason
```

### 4. Planner

Reçoit la sortie du Critic. Produit un JSON de fixes :

```json
[
  {"file": "main.py", "reason": "manque pygame.init()"}
]
```

### 5. Coder (fix)

Reçoit le fichier actuel + reason. Réécrit le fichier complet avec le fix appliqué.

---

## Diagnostic — ce qui ne marchait pas et pourquoi

| Symptôme | Cause | Solution appliquée |
|----------|-------|-------------------|
| Spec vague (`main game loop`) | Prompt Architect pas assez contraignant | Prompt avec format de sortie strict + exemples |
| Fichiers corrompus (`obj['content']`) | Format `<tool>` fragile, parsing raté | Switch vers blocs ` ```python ` + validation syntaxe immédiate |
| Code incomplet (stubs sans logique) | Coder générait 1 fichier → voyait pas les autres | Context cumulatif : chaque fichier déjà généré est ajouté au prompt |
| Imports manquants ou en double | LLM pas guidé sur les imports standards | Prompt coder avec liste explicite des imports nécessaires |
| Modèle 1.5B = garbage | Trop petit pour code complexe | 1.5B recommandé pour Planner uniquement; Architect/Coder = 3B minimum |

---

## Journal de tests

| Date | Modèle | Prompt | Spec | Code | Syntax OK | Jouable | Notes |
|------|--------|--------|------|------|-----------|---------|-------|
| 2026-04-25 | Qwen 1.5B Q8 | "Space Invaders minimal avec son" | ✗ | ✗ | ✗ | - | Spec vague + fichiers corrompus |
| 2026-04-25 | Qwen 3B Q6 | (pas encore testé) | - | - | - | - | - |
| 2026-04-25 | Qwen 7B Q5 | (pas encore testé) | - | - | - | - | - |

---

## Pourquoi ce projet existe

- **LLMs locaux** = inférence rapide, zéro rate limit, données hors cloud
- **Game dev** = itération rapide, feedback visuel immédiat
- **Pattern Architect/Coder/Critic** = bien adapté aux tâches structurées avec vérification
- **But final** = prompts suffisamment bons pour qu'un 3B produise du code production-ready sur n'importe quel petit projet Python

Le moteur doit devenir **neutre et générique** : à terme, un prompt du style "build a CLI todo app with SQLite" doit réussir sans modification du code.

---

## Projets voisins

- [Nova-Atlas](https://github.com/nikodindon/nova-atlas) — AI news engine + radio
- [Nova-Blog](https://github.com/nikodindon/nova-blog) — blog automation from Hermes sessions
- [local-intent-coder](https://github.com/nikodindon/local-intent-coder) — code generator generaliste
- [Stellar Siege](https://github.com/nikodindon/stellar-siege) — Space Invaders de référence codé à la main
