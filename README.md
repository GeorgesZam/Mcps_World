# mcpGPT

mcpGPT est une application Streamlit qui offre une interface de chat enrichie, inspirée de l'UI de ChatGPT, avec gestion d'authentification et contrôle d'accès aux outils.

## Fonctionnalités

- **Authentification** :  
  - Trois rôles prédéfinis : `normal`, `admin`, `root`.  
  - Accès différencié aux outils selon le rôle (normal sans outils, admin/root avec outils).

- **Interface de chat** :  
  - Utilisation de `st.chat_message` et `st.chat_input` pour une expérience utilisateur moderne.  
  - Téléchargement de fichiers directement dans la page de chat (PDF, Excel, Word, PowerPoint, TXT, CSV).  
  - Le contenu des fichiers est automatiquement extrait et inclus dans le contexte de la conversation.

- **Page de configuration API** :  
  - Mettre à jour l’`api_type`, `api_base`, `api_key`, `api_version`, et le modèle (`model`).  
  - Enregistrement dynamique et initialisation d’OpenAI.

- **Gestion des outils** :  
  - Chargement automatique des scripts `tools/tool-*.py`.  
  - Admin et root peuvent uploader, lister et supprimer des outils via l’interface.

## Installation

1. Cloner le dépôt :  
   ```bash
   git clone https://votre-repo/mcpGPT.git
   cd mcpGPT
   ```

2. Installer les dépendances :  
   ```bash
   pip install -r requirements.txt
   ```

3. Lancer l’application :  
   ```bash
   streamlit run improved_mcpGPT.py
   ```

## Authentification

Les identifiants par défaut sont définis dans `improved_mcpGPT.py` :

```python
CREDENTIALS = {
    "normal": "normal_pass",
    "admin":  "admin_pass",
    "root":   "root_pass"
}
```

Vous pouvez modifier ces valeurs selon vos besoins.

## Personnalisation

- **Configurer l’API OpenAI** dans `DEFAULT_CONFIG`.  
- **Ajouter vos propres outils** dans le dossier `tools/`, en respectant la structure :
  ```python
  function_schema = { ... }
  description = "Description de l’outil"
  def function_call(...):
      ...
  ```

## Licence

MIT
