"""
Phase 24: LLM-Driven Script Understanding.
Uses DeepSeek API to intelligently extract asset requirements from script data.
"""
import os
import json
import requests
from typing import List, Dict, Any, Optional

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "models.json")

def _load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def extract_assets_via_llm(chapters: List[Dict], characters: Optional[List[Dict]] = None) -> List[Dict[str, Any]]:
    """
    Uses DeepSeek to intelligently parse script chapters and extract
    ALL asset requirements, including implicit ones.
    
    Returns a list of candidate assets with type, name, description.
    """
    config = _load_config().get("deepseek", {})
    api_key = config.get("api_key", "")
    base_url = config.get("base_url", "https://api.deepseek.com/v1")
    model = config.get("model", "deepseek-chat")
    
    if not api_key:
        return []
    
    # Build a compact summary of the script for the LLM
    script_summary = _build_script_summary(chapters, characters)
    
    system_prompt = """你是一个游戏素材需求分析专家。用户会给你一段视觉小说/互动游戏的剧本。
你的任务是从剧本中提取所有需要制作的游戏素材。请仔细阅读全文，不要遗漏任何隐藏的素材需求。

包括：
1. **人物立绘** — 每个登场角色都需要。提取他们的隐含情绪、外貌、服装特征、气质。如果有换装，作为单独需求提取。
2. **背景图** — 随着故事发展提到的每个独特场景。详细描述环境、光线、天气和氛围。
3. **道具图** — 剧情中出现的关键物品（如：匕首、信件、宝石等）。描述其材质、光泽、外观。
4. **剧情CG** — 剧情中发生的关键动作事件特写（如：两人相拥、主角跳下悬崖）。详细描述画面构图、动作、整体情境。
5. **BGM** — 提取情绪氛围需要配套的音乐。
6. **音效** — 提取场景、动作情节中隐含的物理拟真声效（如：开门声、风声、脚步声、打斗声）。

特别注意：
- 仔细阅读全文，从开始到结束的所有场景都要提取，切勿只看开头！
- 不要遗漏对话中**隐含提到**的场景。
- 角色描述要包含视觉特征，适合FLUX类模型AI绘画使用。

严格按以下JSON格式回复（不要添加其他内容）：
```json
[
  {"type": "人物立绘", "name": "角色名", "description": "详细外貌描述，适合FLUX/AI绘画，包含镜头、发型、服装"},
  {"type": "背景图", "name": "场景名", "description": "详细场景描述，适合FLUX/AI绘画，包含光照、构图"},
  {"type": "道具图", "name": "物品名", "description": "详细物品材质及发光设定"},
  {"type": "剧情CG", "name": "场景动作名", "description": "包含画面镜头构图、人物动态交互的详细画面描述"},
  {"type": "BGM", "name": "音乐名", "description": "风格、情绪、乐器描述"},
  {"type": "音效", "name": "声音名", "description": "具体发生的物理声音、环境拟真音描述"}
]
```"""

    # We send up to 30000 chars safely, instead of short snippets
    user_prompt = f"以下是剧本内容，请提取全剧本的大量素材需求：\n\n{script_summary[:30000]}"
    
    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 4000
            },
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"[LLM Extractor] API Error: {response.status_code} - {response.text[:200]}")
            return []
        
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        
        # Extract JSON from response (handle markdown code blocks)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        assets = json.loads(content.strip())
        
        # Add default fields
        for asset in assets:
            asset["selected"] = True
            safe_name = asset["name"].replace(" ", "_").replace("/", "_")
            if asset["type"] == "人物立绘":
                asset["path"] = f"assets/portraits/{safe_name}.png"
            elif asset["type"] in ["场景", "背景图"]:
                asset["type"] = "背景图"
                asset["path"] = f"assets/backgrounds/{safe_name}.png"
            elif asset["type"] == "道具图":
                asset["path"] = f"assets/items/{safe_name}.png"
            elif asset["type"] == "剧情CG":
                asset["path"] = f"assets/cgs/{safe_name}.png"
            elif asset["type"] == "BGM":
                asset["path"] = f"assets/bgm/{safe_name}.mp3"
            elif asset["type"] == "音效":
                asset["path"] = f"assets/sfx/{safe_name}.wav"
            else:
                asset["path"] = f"assets/other/{safe_name}.png"
        
        return assets
        
    except Exception as e:
        print(f"[LLM Extractor] Error: {e}")
        return []


def _build_script_summary(chapters: List[Dict], characters: Optional[List[Dict]] = None) -> str:
    """Build a compact text summary from chapter data for LLM consumption."""
    lines = []
    
    # Character info
    if characters:
        lines.append("【已知角色】")
        for c in characters[:20]:  # Cap at 20
            name = c.get("name", c.get("id", "Unknown"))
            desc = c.get("description", "")
            lines.append(f"- {name}: {desc}")
        lines.append("")
    
    # Chapter summaries (no more harsh limits, allow deep extraction)
    for i, ch in enumerate(chapters):
        title = ch.get("title", f"第{i+1}章")
        lines.append(f"【{title}】")
        nodes = ch.get("nodes", [])
        for node in nodes:  # Process all nodes instead of just 8
            speaker = node.get("speaker", "")
            text = node.get("text", "")
            bg = node.get("bg", "")
            music = node.get("music", "")
            
            parts = []
            if bg:
                parts.append(f"[场景:{bg}]")
            if music:
                parts.append(f"[BGM:{music}]")
            if speaker and text:
                parts.append(f"{speaker}: {text}")
            elif text:
                parts.append(text)
            
            if parts:
                lines.append("  " + " ".join(parts))
        
        lines.append("")
    
    return "\n".join(lines)


def enhance_prompt_via_llm(asset_type: str, description: str, nar_context: str = "") -> str:
    """
    Uses DeepSeek to enhance a raw asset description into a high-quality
    AI generation prompt (for Stable Diffusion / SDXL).
    """
    config = _load_config().get("deepseek", {})
    api_key = config.get("api_key", "")
    base_url = config.get("base_url", "https://api.deepseek.com/v1")
    model = config.get("model", "deepseek-chat")
    
    if not api_key:
        return description
    
    if asset_type in ["人物立绘", "背景图", "道具图", "剧情CG"]:
        if asset_type == "人物立绘":
            system_prompt = """你是一个AI绘画提示词专家，专精于 FLUX 和 SDXL 等前沿模型。将用户给出的角色描述转化为极高品质的英文生成提示词。

要求：
- 仅输出纯英文提示词，用逗号分隔，按重要性排序。
- 必须包含极高品质触发词：masterpiece, best quality, ultra-detailed, highly detailed illustration, 8k resolution, perfect anatomy
- 必须包含主体描述：1girl/1boy/man/woman, 面部特征, 发型, 瞳色, 详细服装。
- 必须包含姿态/视角：standing, looking at viewer, expression details (e.g., slight smile, serious)。
- 必须包含风格要求：anime visual novel style, clean crisp lineart, soft cel shading, beautiful gorgeous colors, professional lighting。
- 背景必须干净：simple background, solid white background（立绘必须有纯色干净背景方便抠图）。
- 绝不要混入：NSFW, simple colors, lowres, bad hands, missing fingers 等负面情况。

只输出最终的英文正向提示词，不要包含任何前缀、中文字符或解释。"""
        elif asset_type == "背景图":
            system_prompt = """你是一个AI绘画提示词专家，专精于 FLUX 和 SDXL 等前沿模型。将场景描述转化为极高品质的英文生成提示词。

要求：
- 仅输出纯英文提示词，用逗号分隔，按重要性排序。
- 必须包含极高品质触发词：masterpiece, best quality, ultra-detailed scenery, breathtaking illustration, 8k resolution, award-winning landscape
- 必须包含场景特征：建筑、环境、道具、材质（如 reflections, glowing, detailed texture）。
- 必须包含光照与氛围：dramatic lighting, cinematic composition, volumetric lighting, god rays (若合适), beautiful lighting。
- 必须包含风格要求：anime visual novel background, concept art, stunning scenery, expansive view, no characters, nobody。
- 绝不要混入人物（no humans, empty scene），确保是纯净场景图。

只输出最终的英文正向提示词，不要包含任何前缀、中文字符或解释。"""
        elif asset_type == "道具图":
            system_prompt = """你是一个AI绘画提示词专家，专精于 FLUX 和 SDXL 等前沿模型。将道具/物品描述转化为极高品质的英文生成提示词。

要求：
- 仅输出纯英文提示词，用逗号分隔。
- 必须包含极高品质触发词：masterpiece, best quality, highly detailed, ultra-detailed item, 8k resolution, photorealistic
- 必须包含主体描述：1 object, solo, detailed macro shot, depth of field。
- 材质和光泽表现：(如 metallic, glowing, rough texture, sparkling)。
- 背景必须干净：simple background, solid black background 或者 solid white background（道具必须有纯色干净背景方便提取轮廓）。

只输出最终的英文正向提示词，不要包含任何前缀、中文字符或解释。"""
        else:
            system_prompt = """你是一个AI绘画提示词专家，专精于 FLUX 和 SDXL 等前沿模型。将动作及互动场景描述转化为极高品质的英文Event CG提示词。

要求：
- 仅输出纯英文提示词，用逗号分隔。
- 必须包含极高品质触发词：masterpiece, best quality, breathtaking illustration, highly detailed, official art, cinematic angle
- 镜头和动作：dynamic angle, action shot, close-up, expression, interacting。
- 多人描述：说明人物的数量及特征（如 2girls/1boy 1girl, hugging, fighting 等）。

只输出最终的英文正向提示词，不要包含任何前缀、中文字符或解释。"""
    else:
        return description  # BGM doesn't need SD prompts
    
    context_hint = f"\n叙事上下文参考: {nar_context}" if nar_context else ""
    
    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"素材类型: {asset_type}\n描述: {description}{context_hint}"}
                ],
                "temperature": 0.5,
                "max_tokens": 500
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        else:
            return description
            
    except Exception as e:
        print(f"[LLM Enhance] Error: {e}")
        return description


def parse_long_text_to_nodes(text: str) -> List[Dict[str, Any]]:
    """
    Phase 45: Smart Text Import.
    Uses DeepSeek to intelligently parse a large block of prose/script text 
    and split it into structured dialogue and narrative nodes.
    """
    config = _load_config().get("deepseek", {})
    api_key = config.get("api_key", "")
    base_url = config.get("base_url", "https://api.deepseek.com/v1")
    model = config.get("model", "deepseek-chat")
    
    if not api_key:
        print("[LLM Smart Import] No API key configured. Falling back to simple split.")
        # Very naive fallback if no AI
        return [{"type": "narrative", "speaker": "", "text": p, "bg": "", "music": ""} 
                for p in text.splitlines() if p.strip()]
    
    system_prompt = """你是一个智能剧本排版助手。用户会给你一大段小说、文章或剧本草稿。
你的任务是将整段长文本按照时间线和剧情发展，拆分成**离散的剧本节点（Nodes）**。

剧本节点分为两种类型：
1. `dialogue`（对白）：角色说话。必须提取出 `speaker`（角色名）和 `text`（说的内容，不要加引号）。
2. `narrative`（旁白）：场景描述、动作、心理活动等。`speaker` 为空，内容放在 `text` 中。

要求：
- 请逐句或逐段分析，保持剧情连贯，不要遗漏原文信息。
- 如果原文中隐含了场景切换，请在 `bg`（背景舞台）中标注出场景发生地（简短词组，如"火车站平台"、"餐车"）。
- 如果你觉得当前节点适合配什么样的音乐，在 `music`（BGM指引）中简短填入（如"紧张悬疑"）。如果不重要可以留空。
- 必须严格返回合法的 JSON 数组，不要夹带任何其他废话或markdown。

输出格式示例：
```json
[
  {
    "type": "narrative",
    "speaker": "",
    "text": "午夜，东方快车停靠在风雪交加的站台。",
    "bg": "火车站站台",
    "music": "风雪声，低沉"
  },
  {
    "type": "dialogue",
    "speaker": "波洛",
    "text": "这封信是伪造的。真凶还在车上。",
    "bg": "火车站站台",
    "music": "悬疑弦乐"
  }
]
```"""

    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"请拆分以下长文本为节点数组：\n\n{text[:20000]}"}
                ],
                "temperature": 0.3,
                "max_tokens": 4000
            },
            timeout=45
        )
        
        if response.status_code != 200:
            print(f"[LLM Smart Import] API Error: {response.status_code} - {response.text[:200]}")
            return []
            
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        nodes = json.loads(content.strip())
        
        # Ensure format conformity
        for node in nodes:
            node.setdefault("type", "narrative")
            node.setdefault("speaker", "")
            node.setdefault("text", "")
            node.setdefault("bg", "")
            node.setdefault("music", "")
            if node["type"] not in ["dialogue", "narrative"]:
                node["type"] = "narrative"
                
        return nodes
        
    except Exception as e:
        print(f"[LLM Smart Import] Error: {e}")
        return []

