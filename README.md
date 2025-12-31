# 🎓 Examen Pratique : Modernisation d'une Plateforme d'Agent Analytique

**Cours** : AI-Agents-MLOps-Course 
**Points totaux** : 20 points


## 🔴 Problématique : Pourquoi Cette Architecture Échoue en Production

L'application `AgenticDataAnalysis` que vous voyez ici est une **première itération fonctionnelle**, mais elle souffre de limitations critiques qui la rendent **inutilisable en production**. Votre tâche est de la transformer en une **plateforme scalable, sécurisée et persistante**.

### 1. 🧠 Perte de Mémoire au Redémarrage (CRITIQUE)
```
Symptôme: À chaque redémarrage, tout l'historique de conversation disparaît
Cause: Pas de persistance des états d'agent
Impact: Apprentissage impossible, utilisateurs doivent repartir de zéro
Exemple: 
  - Utilisateur 1 demande "Analyse le revenu moyen" → Agent répond
  - Redémarrage de l'app
  - Utilisateur 1 demande une question de follow-up → Agent ne se souvient de rien
```

**Solution du Cours (Chapitre 4)**  
Implémenter un **checkpointer PostgreSQL avec LangGraph** qui persiste l'état complet de l'agent en base de données.

### 2. 👥 Pas de Multi-Utilisateurs (CRITIQUE)
```
Symptôme: Pas d'authentification, toutes les données sont partagées
Cause: Architecture monolithique Streamlit
Impact: Risque majeur de sécurité et violation de confidentialité
Exemple:
  - Utilisateur A upload son dataset personnel → Utilisateur B le voit aussi
  - Aucune isolation des données
  - Aucune conformité RGPD/HIPAA
```

**Solution du Cours**  
- Authentification JWT avec FastAPI
- Modèle utilisateur avec SQLAlchemy
- Isolation par `user_id` partout

### 3. 💾 Volatilité Complète des Résultats (GRAVE)
```
Symptôme: Toutes les visualisations et analyses sont perdues au redémarrage
Cause: Pas de base de données
Impact: Aucune traçabilité, aucune conformité réglementaire
Exemple:
  - Utilisateur exporte un rapport → Crash serveur
  - Le rapport est perdu, utilisateur doit tout refaire
```

**Solution du Cours**  
- PostgreSQL pour stocker les visualisations
- Format JSON Plotly pour persistance fiable

### 4. 📈 Absence de Scalabilité (GRAVE)
```
Symptôme: Un seul processus Streamlit, impossible de gérer plusieurs requêtes
Cause: Architecture monolithique
Impact: Effondrement sous charge, downtime
Exemple:
  - 2 utilisateurs font des requêtes simultanées → L'app se bloque
  - Une requête longue bloque toutes les autres
  - Impossible d'ajouter des workers
```

**Solution du Cours (Chapitre 5)**  
- Backend FastAPI (stateless, scalable)
- File d'attente Celery pour traitements asynchrones
- Architecture microservices

### 5. 🔐 Exécution de Code Non Sécurisée (CRITIQUE)
```
Symptôme: Code Python exécuté directement sans validation
Cause: exec() ou eval() sans sandbox
Impact: Injection de code, vol de données, sabotage
Exemple:
  - Attaquant soumet: "__import__('os').system('rm -rf /')"
  - Code exécuté directement → Perte de données
```

**Solution du Cours**  
- RestrictedPython pour exécution sécurisée
- Limitations de ressources (timeouts, RAM)
- Whitelist de modules approuvés

---

## 📋 Phases d'Implémentation

### ✅ Phase 1 : Analyse et Conception (2 points)
**Objectif** : Comprendre le problème et proposer une solution

- [ ] Analyser l'application existante
- [ ] Documenter les 5 limitations dans `docs/ARCHITECTURE_ANALYSIS.md`
- [ ] Proposer une architecture cible
- [ ] Créer un diagramme UML/C4 de l'architecture moderne

**Fichier à créer** : `docs/ARCHITECTURE_ANALYSIS.md`

---

### 🔧 Phase 2 : Backend Production-Ready (6 points)
**Objectif** : Construire les fondations pour la scalabilité

**2.1 API FastAPI**
- [ ] Créer `backend/api/main.py` avec FastAPI
- [ ] Ajouter CORS middleware
- [ ] Implémenter error handling global
- [ ] Setup logging structuré

**2.2 Authentification & Utilisateurs**
- [ ] Modèle `User` avec SQLAlchemy
- [ ] Routes `/api/auth/register` et `/api/auth/login`
- [ ] JWT tokens avec expiration
- [ ] Protection des routes avec `get_current_user`

**2.3 Modèles de Données**
- [ ] `User` : email, mot de passe hashé, timestamps
- [ ] `Dataset` : proprietaire (FK User), métadonnées
- [ ] `AnalysisSession` : user_id, status, messages
- [ ] `Visualization` : session_id, figure_json

**2.4 Migration Agent LangGraph**
- [ ] Créer `backend/agents/agent_manager.py`
- [ ] **IMPORTANT** : Implémenter checkpointer PostgreSQL (Chapitre 4)
- [ ] Gérer les sessions avec thread_id = session_id

**2.5 Sécurité : Code Sandbox**
- [ ] Créer `backend/security/code_sandbox.py`
- [ ] Implémenter RestrictedPython
- [ ] Timeouts avec signal/threading
- [ ] Whitelist de modules (pandas, numpy, sklearn)

**2.6 Celery & Async**
- [ ] Configuration Celery avec Redis
- [ ] Task pour traitement analyse
- [ ] Queue séparation (analysis, datasets)

---

### 💾 Phase 3 : Persistance Robuste (4 points)
**Objectif** : S'assurer que rien n'est jamais perdu

- [ ] PostgreSQL avec migrations Alembic
- [ ] **Checkpointer LangGraph en base PostgreSQL** (Chapitre 4 du cours)
- [ ] Sessions utilisateur persistantes
- [ ] Visualisations stockées en JSON
- [ ] Historique des analyses avec timestamps

**Important** : C'est ici qu'on résout le problème #1 (perte de mémoire)

---

### 🎨 Phase 4 : Frontend et Intégration (4 points)
**Objectif** : Moderniser l'interface sans réinventer la roue

- [ ] Refactoriser Streamlit pour appeler le backend
- [ ] Client API avec gestion de sessions
- [ ] Login/register dans l'UI
- [ ] Afficher l'historique des analyses
- [ ] Amélioration UX globale

---

### 🚀 Phase 5 : Déploiement et Tests (4 points)
**Objectif** : S'assurer que tout fonctionne réellement

**5.1 Dockerisation**
- [ ] `Dockerfile.backend` pour FastAPI
- [ ] `Dockerfile.frontend` pour Streamlit
- [ ] `Dockerfile.celery` pour worker
- [ ] `docker-compose.yml` complet

**5.2 Tests Fonctionnels (OBLIGATOIRES)**
- [ ] `backend/tests/test_agent_integration.py` : Tests d'agent
- [ ] `backend/tests/test_api.py` : Tests d'API
- [ ] `backend/tests/test_persistence.py` : Tests de persistance
- [ ] `backend/tests/test_security.py` : Tests de sécurité

**5.3 Logging & Monitoring**
- [ ] Logging structuré avec structlog
- [ ] Health checks pour chaque service
- [ ] Métriques de base

---

## 🧪 Tests Fonctionnels (OBLIGATOIRES)

### Test d'Intégration Agent (`backend/tests/test_agent_integration.py`)
```python
@pytest.mark.asyncio
async def test_describe_dataset():
    # Vérifier que l'agent peut décrire un dataset
    pass

@pytest.mark.asyncio
async def test_session_persistence():
    # CRITIQUE: Vérifier que l'agent se souvient après restart
    pass

@pytest.mark.asyncio
async def test_code_sandbox():
    # Vérifier que le code malveillant est bloqué
    pass
```

### Tests d'API (`backend/tests/test_api.py`)
```python
def test_auth_register():
    # Vérifier que les utilisateurs peuvent s'inscrire
    pass

def test_unauthorized_access():
    # Vérifier que l'accès sans token est refusé
    pass
```

### Tests de Persistance (`backend/tests/test_persistence.py`)
```python
def test_user_data_isolation():
    # CRITIQUE: User A ne voit pas les données de User B
    pass

def test_visualization_storage():
    # Vérifier que les figures persistent
    pass
```

### Tests de Sécurité (`backend/tests/test_security.py`)
```python
def test_sql_injection():
    # Vérifier que les injections SQL sont impossible
    pass

def test_resource_limits():
    # Vérifier que les timeouts sont appliqués
    pass
```

**Pour passer les tests :**
```bash
pip install -r requirements-test.txt
pytest backend/tests/ -v --cov=backend
```

---

## 📦 Livrables Obligatoires

### 1. Repository Git
- [ ] Code complet et fonctionnel
- [ ] Historique de commits clairs
- [ ] Branch `main` avec code production-ready
- [ ] `.gitignore` approprié (pas de secrets, uploads, __pycache__)

### 2. Tests Fonctionnels
- [ ] `backend/tests/test_*.py` avec ≥ 70% de couverture
- [ ] Tous les tests passent : `pytest backend/tests/ -v`
- [ ] `pytest.ini` configuré
- [ ] `requirements-test.txt` avec dépendances

### 3. Docker Compose Opérationnel
```bash
# Doit fonctionner sans intervention manuelle
docker-compose up -d

# Tous les services doivent être healthy
docker-compose ps
```

Services requis :
- PostgreSQL (port 5432)
- Redis (port 6379)
- Backend FastAPI (port 8000)
- Frontend Streamlit (port 8501)
- Celery Worker
- Celery Flower (monitoring, port 5555)

### 4. Documentation Technique
- [ ] `docs/ARCHITECTURE.md` - Diagramme et explications
- [ ] `docs/SETUP.md` - Instructions de déploiement
- [ ] `docs/API.md` - Documentation des endpoints
- [ ] `docs/ARCHITECTURE_ANALYSIS.md` - Analyse ancien/nouveau

### 5. Validation Fonctionnelle
- [ ] Tests qui démontrent le bon fonctionnement
- [ ] Preuve que les 5 problèmes sont résolus
- [ ] Script de validation manuel (optionnel)

---

## ✅ Critères d'Évaluation (Total : 20 points)

| Catégorie | Points | Critères |
|-----------|--------|----------|
| **Architecture** | 4 | Cohérence, séparation des responsabilités, choix techniques |
| **Implémentation** | 6 | Qualité du code, lisibilité, gestion des erreurs |
| **Sécurité** | 5 | Sandbox, authentification, secrets, injections |
| **Persistance** | 3 | **Checkpointer PostgreSQL**, sessions, visualisations |
| **Tests & Déploiement** | 2 | Suite de tests, docker-compose, documentation |

### Points Clés de Notation

**CRUCIAL** : Le checkpointer PostgreSQL doit fonctionner réellement
- Arrêter le backend → L'agent reprend où il s'était arrêté ✅
- Pas juste une mémoire en mémoire ❌

**Sécurité** : Code Python exécuté doit être sécurisé
- `__import__('os').system('malveillant')` → BLOQUÉ ✅
- Timeouts appliqués ✅
- Pas d'accès aux fichiers système ✅

**Tests** : Doivent démontrer les solutions
- Test que l'authentification marche
- Test que les utilisateurs sont isolés
- Test que les visualisations persistent
- Test que le code malveillant est bloqué

---

## 🚀 Pour Commencer

### 1. Cloner et Setup Initial
```bash
git clone <this-repo>
cd AgenticDataAnalysis-Exam

# Créer une branche de travail
git checkout -b feat/modernization
```

### 2. Analyser l'Application Actuelle
Lisez attentivement :
- `data_analysis_streamlit_app.py` - Point d'entrée
- `Pages/backend.py` - Logique de l'agent
- `Pages/graph/` - État et nodes LangGraph

Documentez les 5 problèmes dans `docs/ARCHITECTURE_ANALYSIS.md`

### 3. Proposer une Architecture
Créez un diagramme montrant :
- Frontend Streamlit isolé
- Backend FastAPI avec routes
- Base de données PostgreSQL
- Cache/Queue Redis
- Agent avec checkpointer

### 4. Implémenter par Phases
- Phase 1 : Documentation ✅ (facile)
- Phase 2 : Backend (cœur) ⚠️ (moyen)
- Phase 3 : Persistance (critique) ⚠️ (moyen)
- Phase 4 : Frontend (optionnel) ✅ (facile)
- Phase 5 : Tests & Deploy ⚠️ (moyen)

### 5. Valider avec Docker
```bash
docker-compose up -d
docker-compose logs -f

# Tester les endpoints
curl -X POST http://localhost:8000/api/auth/register

# Voir l'interface
open http://localhost:8501
```

---

## 📚 Ressources & Références

### Chapitres du Cours Critiques
- **Chapitre 4** : Memory + Checkpointer PostgreSQL
- **Chapitre 5** : Microservices Architecture

### Technologies Requises
- **FastAPI** : Backend moderne
- **SQLAlchemy** : ORM pour PostgreSQL
- **LangGraph** : Orquestration agent
- **Celery** : Queue asynchrone
- **RestrictedPython** : Sandbox pour code
- **PostgreSQL** : Base persistante
- **Redis** : Cache et queue

### Commandes Utiles
```bash
# Démarrer les services
docker-compose up -d

# Voir les logs
docker-compose logs -f backend

# Accéder à PostgreSQL
docker-compose exec postgres psql -U user -d database

# Accéder à Redis
docker-compose exec redis redis-cli

# Lancer les tests
pytest backend/tests/ -v

# Voir la couverture
pytest backend/tests/ --cov=backend
```

---

## 📝 Soumission

**Deadline** : [À définir]

**À soumettre**
1. URL du repository GitHub
2. Preuve que `docker-compose up` fonctionne
3. Résultats des tests : `pytest backend/tests/ -v`

**Critères d'acceptation**
- ✅ Tous les tests passent
- ✅ Checkpointer PostgreSQL fonctionne
- ✅ Authentification multi-utilisateur
- ✅ Code sandbox sécurisé
- ✅ Documentation complète

---

## 🤔 Questions Fréquentes

**Q: Je dois implémenter Chapitre 5 (microservices) complètement ?**  
A: Non. Phase 2 demande FastAPI + Celery, ce qui est suffisant. Une architecture entièrement distribuée (7 services) n'est pas nécessaire.

**Q: Est-ce que je peux utiliser OpenAI au lieu d'Ollama ?**  
A: Oui, mais gérez les secrets proprement avec `.env` et des variables d'environnement.

**Q: Quelle est la couverture de tests requise ?**  
A: Au minimum 70%. L'idéal est > 85%.

**Q: Je peux modifier l'interface Streamlit librement ?**  
A: Oui, du moment qu'elle fonctionne et démontre les fonctionnalités.

**Q: Le checkpointer PostgreSQL est vraiment obligatoire ?**  
A: **OUI**. C'est le point clé du Chapitre 4 du cours. Sans lui, vous perdez 3 points.

---

**Bonne chance ! 🎯**
