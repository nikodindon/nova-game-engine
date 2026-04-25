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
# 1. Telecharge un modele GGUF
mkdir -p ~/llm_models/llama3-8b
# Telecharge Meta-Llama-3-8B-Instruct-Q4_K_M.gguf depuis HuggingFace
# ou utilise un modele plus leger pour laptop (Mistral 7B Q5, etc.)

# 2. Lance llama-server
llama-server \
  -m ~/llm_models/llama3-8b/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf \
  -c 8192 \
  -tb 12 \
  -ngl 0 \
  --host 127.0.0.1 \
  --port 8081

# Le flag -ngl 0 = CPU only (pas de GPU needed)
# -tb 12 = 12 threads CPU
```

### Option B : Ollama CLI

```bash
# Installe Ollama, puis :
ollama pull qwen2.5-coder:7b   # ou autre modele
```

---

## Utilisation

```bash
# Generer un jeu depuis un prompt
python main.py "Space Invaders avec des aliens pixel art et des explosions"

# Donner un nom de session
python main.py --session stellar-siege "Breakout game avec power-ups"

# Lister les sessions passees
python main.py --list

# Rejouer une session
python main.py --play stellar-siege_20250425_143022
```

---

## Configuration

Editer `config.json` :

```json
{
  "provider": "llama-server",
  "model": "Meta-Llama-3-8B-Instruct-Q4_K_M.gguf",
  "base_url": "http://localhost:8081",
  "timeout": 300,
  "temperature": 0.1,
  "max_out_tokens": 4096
}
```

Pour Ollama (Option B) :

```json
{
  "provider": "ollama",
  "model": "qwen2.5-coder:7b",
  "base_url": "http://localhost:11434",
  "timeout": 300,
  "temperature": 0.1,
  "max_out_tokens": 4096
}
```

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

## Modeles testes

| Modele | Format | Taille | Laptop (CPU) | Remarks |
|--------|--------|--------|-------------|---------|
| Meta-Llama-3-8B-Instruct | Q4_K_M | ~4.9Go | Lent (30s/token) | Fonctionne |
| Meta-Llama-3-8B-Instruct | Q5_K_M | ~5.7Go | Tres lent | Fonctionne |
| Meta-Llama-3-8B-Instruct | IQ3_M | ~3.3Go | Plus rapide | Fonctionne |
| Mistral-7B-Instruct | Q5 (??? Go) | ??? | Non teste | GGUF disponible |

**Laptop de test** : PC standard, CPU only, pas de GPU dedie.

---

## Notes d'experimentation

### llama-server sur laptop (CPU only)

- Context size 8192 est le minimum pour que le Critic puisse verifier
  plusieurs fichiers en une seule passe.
- Threads (`-tb`) : autant que de cores dispo (8-12 sur un laptop recent).
- Quantization IQ3_M donne le meilleur compromis vitesse/qualite sur CPU.
- Q4_K_M est le plus stable.
- premiere generation de spec = ~30-60s
- cycle de fix = ~20-40s selon longueur du fix

### Pièges observés

- Le Coder LLM parfois ne parse pas correctement le tool call `write_file`
  → le critic detecte le fichier manquant -> deuxieme cycle corrige
- Modell llama3-8b a tendance agenerate des `import pygame` en double
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
