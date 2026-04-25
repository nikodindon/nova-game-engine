# Nova Game Engine

Generateur de jeux Python + Pygame depuis un prompt en langage naturel.
Architect -> Coder -> Critic en boucle, 100% local.

---

## Comment ca marche

```
User prompt  ->  Architect  ->  SPEC.md
                             ->
                        Coder genere
                             ->
                        Critic verifie
                             ->
                   [boucle fix x 3 si besoin]
                             ->
                          Joue !
```

1. **Architect** - Analyse le prompt, produit un SPEC.md structure
2. **Coder** - Genere chaque fichier Python depuis la spec (pattern tool call)
3. **Critic** - Verifie que chaque feature de la spec est implementee
4. **Planner** - Produit un plan de fix si le Critic trouve des problemes
5. Boucle: Coder corrige -> Critic re-verifie (max 3 tours)

---

## Install

```bash
# Dependances systeme
pip install pygame numpy

# Ce projet
git clone https://github.com/nikodindon/nova-game-engine.git
cd nova-game-engine
pip install -r requirements.txt
```

---

## LLM local — Setup obligatoire

Le moteur necessite un serveur LLM local. Deux options :

### Option A : llama-server (recommandee, meme setup que Nova-Atlas)

```bash
# Telecharge un modele GGUF depuis HuggingFace
# Garde le dans ~/llm_models/<model>/

# Lance llama-server (CPU only = -ngl 0)
llama-server \
  -m ~/llm_models/llama3-8b/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf \
  -c 8192 \
  -tb 12 \
  -ngl 0 \
  --host 127.0.0.1 \
  --port 8081

# Flags :
#   -ngl 0   = CPU only (pas de GPU needed)
#   -tb 12   = 12 threads CPU (ajuste selon ton CPU)
#   -c 8192  = context size (minimum pour que Critic puisse verifier plusieurs fichiers)
```

### Option B : Ollama CLI

```bash
# Installe Ollama, puis :
ollama pull qwen2.5-coder:7b
```

---

## Progression des modeles — "crescendo"

On progresse du plus faible au plus fort pour comprendre progressivement
les limites et les seuils de capacite. Chaque palier doit arriver
a produire un Space Invaders jouable.

| Niveau | Modele | Taille | Objectif |
|--------|--------|--------|----------|
| 1 | Qwen2.5-Coder 1.5B Q8 | ~1.6Go | Spec tres simple, code minimal |
| 2 | Qwen2.5-Coder 3B Q6 | ~2.5Go | Spec complete, code jouable (peut louper des features) |
| 3 | Qwen2.5-Coder 7B Q5 | ~4.5Go | Bon code, moins de bugs, imports OK |
| 4 | Llama3 8B IQ3_M | ~3.3Go | Meilleur raisonnement architectural |
| 5 | Llama3 8B Q4_K_M | ~4.9Go | Notre baseline stable |
| 6 | Llama3 8B Q5_K_M | ~5.7Go | Qualite max CPU |

**Echelle Laptop** : PC standard, CPU only, 12 threads, 11Go RAM.

### Telechargement models (HuggingFace CLI)

```bash
# Niveau 1 - Qwen2.5-Coder 1.5B Q8 (~1.6Go)
huggingface-cli download Qwen/Qwen2.5-Coder-1.5B-Instruct-Q8_0.gguf \
  --local-dir ~/llm_models/qwen-1.5b \
  --local-dir-use-symlinks False

# Niveau 2 - Qwen2.5-Coder 3B Q6 (~2.5Go)
huggingface-cli download Qwen/Qwen2.5-Coder-3B-Instruct-Q6_K.gguf \
  --local-dir ~/llm_models/qwen-3b \
  --local-dir-use-symlinks False

# Niveau 3 - Qwen2.5-Coder 7B Q5 (~4.5Go)
huggingface-cli download Qwen/Qwen2.5-Coder-7B-Instruct-Q5_K_M.gguf \
  --local-dir ~/llm_models/qwen-7b \
  --local-dir-use-symlinks False

# Niveaux 4-6 - Llama3 8B (deja telecharges)
# ~/llm_models/llama3-8b/Meta-Llama-3-8B-Instruct-*.gguf
```

---

## Strategie multi-modele par agent

Chaque agent a un role different — un modele adapte peut etre plus
efficace qu'un seul modele pour tout.

| Agent | Modele recommande | Pourquoi |
|-------|------------------|---------|
| **Architect** | Llama3 8B (Q4+) | Bon raisonnement structure, spec bien organisee |
| **Coder** | Qwen2.5-Coder 3B+ | Spécifique code Python, meilleurs imports/utils |
| **Critic** | Llama3 8B (Q4+) | Contexte long, analyse fine de plusieurs fichiers |
| **Planner** | N'importe quel modele (3B+) | JSON borne, prompt court |

**Config multi-modele (avance, pour apres les tests) :**

```json
{
  "agents": {
    "architect": {"model": "Meta-Llama-3-8B-Instruct-Q4_K_M.gguf", "provider": "llama-server"},
    "coder":     {"model": "Qwen2.5-Coder-7B-Instruct-Q5_K_M.gguf", "provider": "llama-server"},
    "critic":    {"model": "Meta-Llama-3-8B-Instruct-Q4_K_M.gguf", "provider": "llama-server"},
    "planner":   {"model": "Qwen2.5-Coder-3B-Instruct-Q6_K.gguf", "provider": "llama-server"}
  },
  "default_base_url": "http://localhost:8081"
}
```

---

## Utilisation

```bash
# Generer un jeu depuis un prompt
python main.py "Space Invaders avec des aliens pixel art et des explosions"

# Avec un modele specifique (remplace dans config.json d'abord)
python main.py --session stellar-siege "Breakout game avec power-ups"

# Lister les sessions passees
python main.py --list

# Rejouer une session
python main.py --play stellar-siege_20250425_143022
```

Pour changer de modele : edite `config.json` puis relance `main.py`.

---

## Configuration

```json
{
  "provider": "llama-server",
  "model": "Qwen2.5-Coder-3B-Instruct-Q6_K.gguf",
  "base_url": "http://localhost:8081",
  "timeout": 300,
  "temperature": 0.1,
  "max_out_tokens": 4096
}
```

| Param | Description |
|-------|-------------|
| provider | `llama-server` (recommandee) ou `ollama` |
| model | Fichier GGUF dans ~/llm_models/ |
| base_url | localhost:8081 (llama-server) ou localhost:11434 (ollama) |
| temperature | 0.1 recommande (0 = boucles, 0.5+ = hors spec) |

---

## Architecture

```
nova-game-engine/
├── main.py              # CLI + boucle principale
├── config.json          # Config LLM (provider, modele, URL)
├── requirements.txt
├── README.md
├── core/
│   ├── config.py        # Chargement config JSON
│   └── llm.py           # Client HTTP -> llama-server OU CLI -> ollama
└── agent/
    ├── architect.py     # Prompt -> SPEC.md
    ├── coder.py         # SPEC.md -> fichiers .py via tool calls
    ├── critic.py        # Verif spec vs code
    ├── planner.py       # Critic -> plan de fix JSON
    ├── prompts.py       # System prompts (Architect/Coder/Critic/Planner)
    └── session.py       # Gestion dossier session + resultats
```

Sessions sauvegardees dans `~/nova-game-engine/sessions/<session_name>/` :
- `SPEC.md` -- spec originale
- `result.txt` -- verdict + review du Critic
- `game/` -- les fichiers Python du jeu

---

## Journal de tests

| Date | Modele | Niveau | Spec OK | Code OK | Jouable | Notes |
|------|--------|--------|---------|---------|---------|-------|
| 2026-04-25 | (pas encore teste) | - | - | - | - | - |

---

## Notes d'experimentation

### llama-server sur laptop (CPU only)

- Context size 8192 est le minimum pour que le Critic puisse verifier
  plusieurs fichiers en une seule passe.
- Threads (`-tb`) : autant que de cores dispo (8-12 sur un laptop recent).
- premiere generation de spec = ~30-60s (selon modele)
- cycle de fix = ~20-40s selon longueur du fix

### Pieges observes

- Le Coder LLM parfois ne parse pas correctement le tool call `write_file`
  -> le critic detecte le fichier manquant -> deuxieme cycle corrige
- Llama3-8b a tendance a generate des `import pygame` en double
  dans certains fichiers -> Critic le detecte
- Temperature 0.1 obligatoire : a 0 le modele peut boucler sur
  des patterns repetitifs, a 0.5+ il sort du code hors spec

---

## Pourquoi ce projet existe

Pour les memes raisons que `local-intent-coder` :
- LLMs locaux = inference rapide, pas de rate limit, pas de cloud
- Game dev = iteration rapide, feedback visuel immediat
- Le pattern Architect/Coder/Critic fonctionne bien pour des taches structurees

Le moteur genere des jeux jouables en < 2 minutes sur un bon CPU.

---

## Projets voisins

- [Nova-Atlas](https://github.com/nikodindon/nova-atlas) — AI news engine + radio
- [local-intent-coder](https://github.com/nikodindon/local-intent-coder) — code generator generaliste
- [Nova-Blog](https://github.com/nikodindon/nova-blog) — blog automation
