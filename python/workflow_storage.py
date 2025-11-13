#!/usr/bin/env python3
"""
WorkflowStorage - Stockage local des workflows (JSON files)
MVP: Simple file storage, pas de DB
"""

import json
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class WorkflowStorage:
    """
    Stockage local des workflows (JSON files)
    MVP: Simple file storage, pas de DB
    """
    
    def __init__(self, storage_dir: str = "./workflows"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        logger.info(f"📁 Workflow storage: {self.storage_dir.absolute()}")
    
    def save(self, workflow: Dict[str, Any], workflow_id: Optional[str] = None) -> str:
        """Sauvegarder un workflow"""
        if not workflow_id:
            workflow_id = f"wf_{uuid.uuid4().hex[:8]}"
        
        workflow['id'] = workflow_id
        
        file_path = self.storage_dir / f"{workflow_id}.json"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(workflow, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Workflow saved: {workflow_id}")
        return workflow_id
    
    def load(self, workflow_id: str) -> Dict[str, Any]:
        """Charger un workflow"""
        file_path = self.storage_dir / f"{workflow_id}.json"
        
        if not file_path.exists():
            raise FileNotFoundError(f"Workflow not found: {workflow_id}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def list_all(self) -> List[Dict[str, Any]]:
        """Lister tous les workflows (summary uniquement)"""
        workflows = []
        
        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    workflow = json.load(f)
                    
                    # Summary uniquement (pas les actions complètes)
                    summary = {
                        'id': workflow.get('id'),
                        'name': workflow.get('name', 'Untitled'),
                        'description': workflow.get('description', ''),
                        'created_at': workflow.get('created_at'),
                        'action_count': len(workflow.get('actions', [])),
                        'duration': workflow.get('duration', 0),
                        'start_url': workflow.get('start_url', '')
                    }
                    workflows.append(summary)
            
            except Exception as e:
                logger.error(f"Failed to load workflow {file_path}: {e}")
        
        # Trier par date de création (plus récent d'abord)
        workflows.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return workflows
    
    def delete(self, workflow_id: str) -> bool:
        """Supprimer un workflow"""
        file_path = self.storage_dir / f"{workflow_id}.json"
        
        if file_path.exists():
            file_path.unlink()
            logger.info(f"🗑️ Workflow deleted: {workflow_id}")
            return True
        
        return False
    
    def update_metadata(self, workflow_id: str, name: str = None, description: str = None) -> bool:
        """Mettre à jour les métadonnées d'un workflow"""
        try:
            workflow = self.load(workflow_id)
            
            if name:
                workflow['name'] = name
            if description:
                workflow['description'] = description
            
            self.save(workflow, workflow_id)
            logger.info(f"✏️ Workflow updated: {workflow_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to update workflow: {e}")
            return False
