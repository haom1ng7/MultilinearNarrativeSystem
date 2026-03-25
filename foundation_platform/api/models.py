from typing import Optional, Dict, Any, List
from pydantic import BaseModel

class AssetRegistrationRequest(BaseModel):
    outline: str

class AssetStatus(BaseModel):
    path: str
    description: str
    task_status: str = "QUEUED"
    last_prompt: str = ""
    logs: List[str] = []

class GenerationRequest(BaseModel):
    asset_path: str
    description: str
    asset_type: str
    provider: str = "mock"
    entropy: float = 0.5
    relationships: Optional[Dict[str, Any]] = None
    refinement_passes: int = 1
    seed: int = -1  # -1 = random
    guidance_scale: float = 7.5
    negative_prompt: str = ""

class NarrativeConfigRequest(BaseModel):
    theme: Optional[str] = None
    era: Optional[str] = None
    social_graph: Optional[Dict[str, Any]] = None
    negative_prompt: Optional[str] = None

class FeedbackRequest(BaseModel):
    asset_path: str
    status: str
    reason: Optional[str] = None
    prompt: str
    context: Dict[str, Any]

class StateUpdateRequest(BaseModel):
    entity_id: str
    trait: str

class ScriptExtractRequest(BaseModel):
    chapters: List[Dict[str, Any]]
    characters: Optional[List[Dict[str, Any]]] = None
    use_llm: bool = True

class VariantGenerateRequest(BaseModel):
    asset_path: str
    description: str
    asset_type: str
    provider: str = "mock"
    count: int = 3
    base_entropy: float = 0.5
    negative_prompt: str = ""
    seed: int = -1  # -1 = random, or specific seed to force variations on fixed base

class DescEnhanceRequest(BaseModel):
    asset_type: str
    description: str

class ParseScriptContentRequest(BaseModel):
    text: str
    model: str = "deepseek-chat"

class ParseScriptContentResponse(BaseModel):
    nodes: List[Dict[str, Any]]

class GodotExportRequest(BaseModel):
    script_json: str  # Full editor store JSON from exportJSON()
