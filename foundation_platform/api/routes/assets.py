import os
from fastapi import APIRouter, HTTPException
from foundation_platform.api.models import AssetRegistrationRequest, ScriptExtractRequest, AssetStatus, ParseScriptContentRequest, ParseScriptContentResponse
from foundation_platform.api.state import asset_registry, extractor, attention_mgr
from foundation_platform.core.llm_service import extract_assets_via_llm, parse_long_text_to_nodes
from foundation_platform.api.services.db_service import save_registry

router = APIRouter(prefix="/assets", tags=["Assets"])

@router.post("/register")
async def register_assets(req: AssetRegistrationRequest):
    global asset_registry
    
    parsed = extractor.parse_outline(req.outline)
    if not parsed:
        raise HTTPException(status_code=400, detail="无法从大纲中提取任何素材需求")
    
    new_registry = extractor.to_registry_dict(parsed)
    for atype, items in new_registry.items():
        if atype not in asset_registry:
            asset_registry[atype] = {}
        for path, desc in items.items():
            asset_registry[atype][path] = AssetStatus(
                path=path,
                description=desc,
                task_status="QUEUED"
            )
    
    attention_mgr.register_assets(parsed)
    
    # Phase 42: Persist registry to disk
    save_registry(asset_registry)
    
    return {
        "message": f"已注册 {len(parsed)} 个素材需求",
        "assets": parsed,
        "total_registered": sum(len(v) for v in asset_registry.values())
    }

@router.post("/extract-from-script")
async def extract_from_script(req: ScriptExtractRequest):
    extraction_mode = "llm"
    candidates = []
    
    if req.use_llm:
        try:
            candidates = extract_assets_via_llm(req.chapters, req.characters)
        except Exception as e:
            print(f"[API] LLM extraction failed: {e}, falling back to regex.")
            candidates = []
    
    if not candidates:
        extraction_mode = "regex"
        speakers = set()
        backgrounds = set()
        music_keys = set()
        scene_descriptions = {}
        character_descriptions = {}
        
        for ch in req.chapters:
            nodes = ch.get("nodes", [])
            for node in nodes:
                speaker = node.get("speaker", "")
                if speaker and speaker != "旁白" and speaker != "narrator":
                    speakers.add(speaker)
                bg = node.get("bg", "")
                if bg:
                    backgrounds.add(bg)
                    text = node.get("text", "")
                    if text and bg not in scene_descriptions:
                        scene_descriptions[bg] = text[:50]
                music = node.get("music", "")
                if music:
                    music_keys.add(music)
        
        if req.characters:
            for c in req.characters:
                cid = c.get("id", "") or c.get("name", "")
                desc = c.get("description", "")
                if cid:
                    character_descriptions[cid] = desc
                    speakers.add(cid)
        
        for speaker in sorted(speakers):
            desc = character_descriptions.get(speaker, f"{speaker}的角色立绘")
            candidates.append({
                "type": "人物立绘", "name": speaker,
                "description": desc, "path": f"assets/portraits/{speaker}.png",
                "selected": True
            })
        for bg in sorted(backgrounds):
            desc = scene_descriptions.get(bg, f"场景: {bg}")
            candidates.append({
                "type": "背景图", "name": bg,
                "description": desc, "path": f"assets/backgrounds/{bg}.png",
                "selected": True
            })
        for music in sorted(music_keys):
            candidates.append({
                "type": "BGM", "name": music,
                "description": f"背景音乐: {music}", "path": f"assets/bgm/{music}.mp3",
                "selected": True
            })
    
    return {
        "message": f"从剧本中提取到 {len(candidates)} 个素材候选 (模式: {extraction_mode})",
        "candidates": candidates,
        "extraction_mode": extraction_mode,
        "stats": {
            "characters": len([c for c in candidates if c.get('type') == '人物立绘']),
            "backgrounds": len([c for c in candidates if c.get('type') == '背景图']),
            "bgm": len([c for c in candidates if c.get('type') == 'BGM'])
        }
    }


@router.post("/parse-script-text", response_model=ParseScriptContentResponse)
async def parse_script_text(req: ParseScriptContentRequest):
    """
    Phase 45: Smart Text Import
    Accepts raw prose/script text and uses LLM to break it down into 
    structured narrative and dialogue nodes.
    """
    try:
        nodes = parse_long_text_to_nodes(req.text)
        if not nodes:
            raise HTTPException(status_code=500, detail="Failed to parse script text. Check API keys or text format.")
        return ParseScriptContentResponse(nodes=nodes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing text: {str(e)}")
