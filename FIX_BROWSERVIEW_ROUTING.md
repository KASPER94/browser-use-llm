# 🐛 FIX: BrowserView ne s'ouvrait pas

## Problème

Quand l'utilisateur cliquait sur "🎬 New Recording" :
- Le message `{"type": "start_recording"}` était envoyé
- Mais il passait par `handle_user_message` → Hybrid Agent
- L'agent essayait de l'interpréter comme une instruction naturelle
- Il tentait `goto('recording_application_url')` → ERREUR
- Le BrowserView ne s'ouvrait jamais

## Logs du problème

```
[Python Error] [2025-11-13 16:56:58,767] INFO - User message: {"type":"start_recording"}
[Python Error] [2025-11-13 16:56:58,767] INFO - 🎯 Using Hybrid Agent (Planning + Rich Observations)
[Python Error] [2025-11-13 16:57:04,170] INFO - 📌 [1] Executing: goto('recording_application_url')
[Python Error] [2025-11-13 16:57:04,175] ERROR - Hybrid agent error: Page.goto: Protocol error (Page.navigate): Cannot navigate to invalid URL
```

## Solution

Modifier `browsergym_server.py` : Ligne 715-728

**Avant** :
```python
if msg_type == 'user_message':
    response = await self.handle_user_message(data.get('message', ''))
```

**Après** :
```python
if msg_type == 'user_message':
    user_msg = data.get('message', '')
    # Essayer de parser comme JSON
    try:
        parsed_msg = json.loads(user_msg)
        if isinstance(parsed_msg, dict) and 'type' in parsed_msg:
            # C'est un message structuré (workflow command)
            msg_type = parsed_msg.get('type')
            data = parsed_msg
            logger.info(f"📦 Parsed structured message: {msg_type}")
    except (json.JSONDecodeError, TypeError):
        pass  # Pas du JSON, message utilisateur normal
```

Maintenant :
- `{"type": "start_recording"}` → routé vers `handle_start_recording()`
- Vrai message utilisateur → routé vers `handle_user_message()` → Agent

## Test

```bash
npm start
```

1. Onglet "📹 Workflows"
2. Cliquer "🎬 New Recording"
3. ✅ Le BrowserView doit s'ouvrir à droite avec Google

---

**Fichier modifié** : `python/browsergym_server.py` (lignes 715-728)
