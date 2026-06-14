import math
from typing import List, Dict, Any, Optional


HERB_DATA = [
    {
        "id": "herb_yuncao",
        "name": "芸香草",
        "latin": "Cymbopogon distans",
        "bencao_ref": "《本草纲目·草部·芸薹》附",
        "dynasty": "明",
        "efficacy": ["驱虫", "防霉", "抑菌"],
        "active_components": ["香茅醛", "香叶醇", "柠檬烯"],
        "target_diseases": ["虫蛀", "霉变"],
        "usage": "阴干研末，撒于书叶之间；或缝制香囊置于书架四角。用量：每册3-5g，每季度更换一次。",
        "contraindications": "气虚血燥者慎用；远离火源，其挥发油易燃。",
        "source_books": ["本草纲目", "遵生八笺"],
        "efficacy_score": 0.88,
        "safety_score": 0.92,
        "aroma_score": 0.85,
        "historical_cases": [
            "宁波天一阁明代建阁之初，即于每书内置芸草，历四百余年虫蛀甚少。",
            "清宫内务府《造办处活计档》载：乾清宫藏籍每年春秋二季更换芸香。",
        ],
    },
    {
        "id": "herb_huangbai",
        "name": "黄柏",
        "latin": "Phellodendron chinense",
        "bencao_ref": "《本草纲目·木部·黄柏》",
        "dynasty": "明",
        "efficacy": ["防虫", "抑菌", "脱酸辅助"],
        "active_components": ["小檗碱", "黄柏碱", "巴马亭"],
        "target_diseases": ["酸化", "虫蛀", "霉变"],
        "usage": "黄柏煎汁（1:10）涂布纸张或书匣内壁；亦可浸制防蠹纸夹入书中。现代研究：小檗碱对纸张pH缓冲能力显著。",
        "contraindications": "直接接触明黄绫封面可能导致轻微褪色，需先做相容性试验。",
        "source_books": ["本草纲目", "齐民要术", "天工开物"],
        "efficacy_score": 0.91,
        "safety_score": 0.80,
        "aroma_score": 0.50,
        "historical_cases": [
            "贾思勰《齐民要术》载：染潢治书法，入潢则经年久不蠹。",
            "敦煌藏经洞唐代写经，多数经潢染处理，千年不蛀。",
        ],
    },
    {
        "id": "herb_aiye",
        "name": "艾叶",
        "latin": "Artemisia argyi",
        "bencao_ref": "《本草纲目·草部·艾》",
        "dynasty": "明",
        "efficacy": ["驱虫", "防霉", "驱螨"],
        "active_components": ["桉叶素", "侧柏酮", "侧柏醇"],
        "target_diseases": ["虫蛀", "霉变"],
        "usage": "端午采艾阴干，搓揉为绒，夹于书脊或制成艾条熏蒸书架。熏蒸法：密闭书库中每10立方米用艾条1支，熏蒸2小时。",
        "contraindications": "熏蒸后需通风4小时以上方可入库；善本纸本不宜直接接触艾油，需用纱布包裹。",
        "source_books": ["本草纲目", "荆楚岁时记"],
        "efficacy_score": 0.82,
        "safety_score": 0.88,
        "aroma_score": 0.78,
        "historical_cases": [
            "《荆楚岁时记》：端午悬艾草门户，以禳毒气；藏书家亦以之入箧。",
            "嘉业堂藏书楼旧规：梅雨季过后以艾烟熏库一次。",
        ],
    },
    {
        "id": "herb_cangzhu",
        "name": "苍术",
        "latin": "Atractylodes lancea",
        "bencao_ref": "《本草纲目·草部·术》",
        "dynasty": "明",
        "efficacy": ["防霉", "抑菌", "辟秽"],
        "active_components": ["苍术素", "茅术醇", "β-桉叶醇"],
        "target_diseases": ["霉变", "酸化"],
        "usage": "苍术片置香炉内燃烟熏蒸，或研磨为末以布袋盛之悬于书橱。亦可煎液雾化喷洒库房。",
        "contraindications": "阴虚内热者不宜久处其烟雾；熏蒸后油墨字迹有极轻微氧化可能，需测试。",
        "source_books": ["本草纲目", "遵生八笺", "千金要方"],
        "efficacy_score": 0.85,
        "safety_score": 0.75,
        "aroma_score": 0.70,
        "historical_cases": [
            "高濂《遵生八笺·起居安乐笺》：藏书于未梅雨时，取苍术烧烟熏之，永无霉黑。",
            "清宫太医院旧方：每岁入夏，内阁大库以苍术、白芷、木香合熏。",
        ],
    },
    {
        "id": "herb_xiangfu",
        "name": "香附子",
        "latin": "Cyperus rotundus",
        "bencao_ref": "《本草纲目·草部·香附子》",
        "dynasty": "明",
        "efficacy": ["防虫", "抑菌", "芳香"],
        "active_components": ["香附烯", "香附醇", "α-香附酮"],
        "target_diseases": ["虫蛀", "霉变"],
        "usage": "香附米炒至微黄，布包裹置于书柜底层，每格50g，半年一换。亦可配伍丁香、藿香制复合香剂。",
        "contraindications": "气虚者久服不宜；惟藏书用无妨。",
        "source_books": ["本草纲目", "居家宜忌"],
        "efficacy_score": 0.78,
        "safety_score": 0.95,
        "aroma_score": 0.90,
        "historical_cases": [
            "明代藏书家胡应麟《少室山房笔丛》：藏书以香附、樟脑为伍，辟蠹胜芸草。",
        ],
    },
    {
        "id": "herb_naohuang",
        "name": "闹黄（藜芦）",
        "latin": "Veratrum nigrum",
        "bencao_ref": "《本草纲目·草部·藜芦》",
        "dynasty": "明",
        "efficacy": ["杀虫", "驱蠹"],
        "active_components": ["藜芦碱", "介芬胺", "藜芦胺"],
        "target_diseases": ["虫蛀"],
        "usage": "藜芦根阴干切片，夹于书脊与封面之间；或研末以极少量撒于蠹穴。严禁内服。",
        "contraindications": "剧毒，仅供外用；操作需戴手套口罩；接触后洗手；严禁用于儿童可接触处。",
        "source_books": ["本草纲目", "天工开物"],
        "efficacy_score": 0.95,
        "safety_score": 0.35,
        "aroma_score": 0.25,
        "historical_cases": [
            "《天工开物·杀青》载：藏书遇蠹，以藜芦纳之，虫立毙。",
        ],
    },
    {
        "id": "herb_baizhi",
        "name": "白芷",
        "latin": "Angelica dahurica",
        "bencao_ref": "《本草纲目·草部·白芷》",
        "dynasty": "明",
        "efficacy": ["驱虫", "芳香", "抑菌"],
        "active_components": ["欧前胡素", "白芷素", "挥发油"],
        "target_diseases": ["虫蛀", "霉变"],
        "usage": "白芷切片研末，与芸草、苍术等份混合，装入绢袋放置书架。",
        "contraindications": "血虚有热者慎用；外用安全。",
        "source_books": ["本草纲目", "太平惠民和剂局方"],
        "efficacy_score": 0.76,
        "safety_score": 0.90,
        "aroma_score": 0.88,
        "historical_cases": [
            "清《四库全书》七阁藏籍，每一函套置白芷、羌活、川芎三合为一囊。",
        ],
    },
    {
        "id": "herb_wuweizi",
        "name": "五味子",
        "latin": "Schisandra chinensis",
        "bencao_ref": "《本草纲目·草部·五味子》",
        "dynasty": "明",
        "efficacy": ["抑菌", "抗氧化", "缓酸化"],
        "active_components": ["五味子素", "五味子醇甲", "木脂素"],
        "target_diseases": ["酸化", "霉变"],
        "usage": "五味子煎汁（1:15）作为脱酸后涂布液，据现代研究其木脂素成分可抑制纸张纤维氧化降解。与黄柏汁合用效果更佳。",
        "contraindications": "对蓝色染料可能有轻微还原作用，需先做小样试验。",
        "source_books": ["本草纲目", "汤液本草"],
        "efficacy_score": 0.72,
        "safety_score": 0.92,
        "aroma_score": 0.55,
        "historical_cases": [
            "现代文物保护研究：五味子提取物在人工加速老化试验中可减少聚合度下降约30%。",
        ],
    },
]

DISEASE_TYPES = ["酸化", "霉变", "虫蛀", "粉化", "撕裂", "水渍", "烟熏", "光老化"]

DISEASE_HERB_MAP = {
    "酸化": ["herb_huangbai", "herb_wuweizi", "herb_cangzhu"],
    "霉变": ["herb_cangzhu", "herb_aiye", "herb_yuncao", "herb_xiangfu", "herb_baizhi"],
    "虫蛀": ["herb_yuncao", "herb_naohuang", "herb_xiangfu", "herb_baizhi", "herb_huangbai"],
    "粉化": ["herb_huangbai", "herb_wuweizi"],
    "光老化": ["herb_wuweizi", "herb_cangzhu"],
    "烟熏": ["herb_aiye", "herb_cangzhu"],
    "水渍": ["herb_cangzhu", "herb_yuncao"],
    "撕裂": [],
}


class KnowledgeGraphService:
    def __init__(self):
        self.herbs = {h["id"]: h for h in HERB_DATA}
        self.disease_map = DISEASE_HERB_MAP

    def get_all_herbs(self) -> List[Dict[str, Any]]:
        return [{k: v for k, v in h.items() if k != "active_components"} for h in HERB_DATA]

    def recommend_herbs(
        self,
        disease_types: Optional[List[str]] = None,
        mold_risk: float = 0.0,
        insect_risk: float = 0.0,
        ph_value: Optional[float] = None,
        top_k: int = 4,
        book_dynasty: str = "",
    ) -> Dict[str, Any]:
        disease_types = disease_types or []
        inferred_diseases = set()
        for dt in disease_types:
            if dt in DISEASE_TYPES:
                inferred_diseases.add(dt)

        if ph_value is not None:
            if ph_value < 5.5:
                inferred_diseases.add("酸化")
                inferred_diseases.add("粉化")
            elif ph_value < 6.0:
                inferred_diseases.add("酸化")
            elif ph_value < 6.5:
                inferred_diseases.add("酸化")

        if mold_risk >= 0.7:
            inferred_diseases.add("霉变")
            inferred_diseases.add("水渍")
        elif mold_risk >= 0.4:
            inferred_diseases.add("霉变")

        if insect_risk >= 0.6:
            inferred_diseases.add("虫蛀")

        inferred_diseases = sorted(inferred_diseases)

        herb_scores: Dict[str, float] = {}
        herb_match_count: Dict[str, int] = {}
        herb_reason: Dict[str, List[str]] = {}

        for disease in inferred_diseases:
            for hid in self.disease_map.get(disease, []):
                herb_scores[hid] = herb_scores.get(hid, 0.0) + 1.0
                herb_match_count[hid] = herb_match_count.get(hid, 0) + 1
                if hid not in herb_reason:
                    herb_reason[hid] = []
                herb_reason[hid].append(disease)

        if mold_risk > 0:
            for hid, h in self.herbs.items():
                if "霉变" in h["target_diseases"] or "防霉" in h["efficacy"] or "抑菌" in h["efficacy"]:
                    herb_scores[hid] = herb_scores.get(hid, 0.0) + mold_risk * 1.2
                    if hid not in herb_reason:
                        herb_reason[hid] = []
                    if "霉菌风险" not in herb_reason[hid]:
                        herb_reason[hid].append("霉菌风险")

        if insect_risk > 0:
            for hid, h in self.herbs.items():
                if "虫蛀" in h["target_diseases"] or "驱虫" in h["efficacy"] or "杀虫" in h["efficacy"] or "驱蠹" in h["efficacy"]:
                    herb_scores[hid] = herb_scores.get(hid, 0.0) + insect_risk * 1.2
                    if hid not in herb_reason:
                        herb_reason[hid] = []
                    if "虫害风险" not in herb_reason[hid]:
                        herb_reason[hid].append("虫害风险")

        if ph_value is not None:
            acid_severity = max(0.0, min(1.0, (7.0 - ph_value) / 2.5))
            if acid_severity > 0:
                for hid, h in self.herbs.items():
                    if "酸化" in h["target_diseases"] or "脱酸辅助" in h["efficacy"] or "缓酸化" in h["efficacy"]:
                        herb_scores[hid] = herb_scores.get(hid, 0.0) + acid_severity * 1.5
                        if hid not in herb_reason:
                            herb_reason[hid] = []
                        if f"pH={ph_value:.2f}" not in herb_reason[hid]:
                            herb_reason[hid].append(f"pH={ph_value:.2f}")

        if book_dynasty:
            for hid, h in self.herbs.items():
                if h.get("dynasty") == book_dynasty:
                    herb_scores[hid] = herb_scores.get(hid, 0.0) * 1.15
                    if hid not in herb_reason:
                        herb_reason[hid] = []
                    if f"朝代匹配:{book_dynasty}" not in herb_reason[hid]:
                        herb_reason[hid].append(f"朝代匹配:{book_dynasty}")

        for hid in herb_scores:
            h = self.herbs[hid]
            herb_scores[hid] = herb_scores[hid] * (0.5 * h["efficacy_score"] + 0.3 * h["safety_score"] + 0.2 * h["aroma_score"])

        sorted_herbs = sorted(herb_scores.items(), key=lambda x: x[1], reverse=True)
        if not sorted_herbs:
            all_sorted = sorted(
                self.herbs.values(),
                key=lambda h: 0.5 * h["efficacy_score"] + 0.3 * h["safety_score"] + 0.2 * h["aroma_score"],
                reverse=True,
            )
            sorted_herbs = [(h["id"], 0.0) for h in all_sorted[:top_k]]

        recommendations: List[Dict[str, Any]] = []
        for hid, score in sorted_herbs[:top_k]:
            h = self.herbs[hid]
            max_score = 2.0
            normalized = max(0.0, min(1.0, score / max_score))
            recommendations.append({
                "herb": {
                    "id": h["id"],
                    "name": h["name"],
                    "latin": h["latin"],
                    "bencao_ref": h["bencao_ref"],
                    "dynasty": h["dynasty"],
                    "efficacy": h["efficacy"],
                    "target_diseases": h["target_diseases"],
                    "usage": h["usage"],
                    "contraindications": h["contraindications"],
                    "source_books": h["source_books"],
                    "efficacy_score": h["efficacy_score"],
                    "safety_score": h["safety_score"],
                },
                "match_score": round(score, 3),
                "confidence": round(normalized, 3),
                "match_reasons": herb_reason.get(hid, []),
                "historical_cases": h.get("historical_cases", []),
            })

        prescription = self._build_prescription(recommendations, inferred_diseases, ph_value, mold_risk, insect_risk)

        return {
            "detected_diseases": inferred_diseases,
            "risk_profile": {
                "ph_value": None if ph_value is None else round(ph_value, 2),
                "mold_risk": round(mold_risk, 3),
                "insect_risk": round(insect_risk, 3),
                "acidification_level": self._acid_level(ph_value) if ph_value is not None else "N/A",
            },
            "recommendations": recommendations,
            "treatment_protocol": prescription,
            "knowledge_nodes": len(self.herbs),
            "disease_links": sum(len(v) for v in self.disease_map.values()),
        }

    def _acid_level(self, ph: Optional[float]) -> str:
        if ph is None:
            return "N/A"
        if ph >= 6.5:
            return "正常"
        if ph >= 6.0:
            return "轻度酸化"
        if ph >= 5.5:
            return "中度酸化"
        return "严重酸化"

    def _build_prescription(
        self,
        recommendations: List[Dict],
        diseases: List[str],
        ph_value: Optional[float],
        mold_risk: float,
        insect_risk: float,
    ) -> Dict[str, Any]:
        steps = []
        step_num = 1

        if "霉变" in diseases or mold_risk >= 0.3:
            steps.append({
                "step": step_num,
                "action": "紧急熏蒸",
                "description": "将藏书移入密闭熏蒸室，以苍术、艾叶等量（每10立方米各100g）燃烟熏蒸4小时，之后通风6小时。每周1次，连续3周。",
                "herbs_used": ["苍术", "艾叶"],
                "priority": "HIGH",
            })
            step_num += 1

        if "虫蛀" in diseases or insect_risk >= 0.3:
            steps.append({
                "step": step_num,
                "action": "深度除蠹",
                "description": "逐一检视书册，以毛刷清除可见虫粪与虫卵；书脊蠹穴注入极少量藜芦酊（藜芦浸75%乙醇，1:5）。处理后置于芸草屉盒中密封30日。",
                "herbs_used": ["藜芦(闹黄)", "芸香草"],
                "priority": "HIGH",
            })
            step_num += 1

        if "酸化" in diseases or (ph_value is not None and ph_value < 6.5):
            steps.append({
                "step": step_num,
                "action": "脱酸处理",
                "description": f"当前pH={ph_value:.2f}。建议采用非水溶液脱酸：氢氧化镁纳米颗粒悬浮液（MgO 0.3mol/L in 异丙醇）喷淋；传统古法：黄柏煎汁（1:10）+五味子煎汁（1:15）等量混合，均匀涂布于纸张两面后阴干。处理后每半年复测pH。",
                "herbs_used": ["黄柏", "五味子"],
                "priority": "MEDIUM" if ph_value and ph_value >= 6.0 else "HIGH",
            })
            step_num += 1

        steps.append({
            "step": step_num,
            "action": "长期藏护方案",
            "description": "每格放置芸草+香附子+白芷三合香囊1枚（每味各20g，纱布包裹）；书架四角各置苍术块50g；每3个月更换一次；梅雨季前后增加一次艾熏蒸。严格控制库温18-22℃、相对湿度45%-55%、光照<50lux。",
            "herbs_used": ["芸香草", "香附子", "白芷", "苍术", "艾叶"],
            "priority": "MEDIUM",
        })

        return {
            "urgency": "CRITICAL" if (mold_risk >= 0.7 or insect_risk >= 0.7 or (ph_value and ph_value < 5.5))
                       else "HIGH" if (mold_risk >= 0.4 or insect_risk >= 0.4 or (ph_value and ph_value < 6.0))
                       else "MEDIUM" if (mold_risk >= 0.2 or insect_risk >= 0.2 or (ph_value and ph_value < 6.5))
                       else "ROUTINE",
            "steps": steps,
            "expected_outcome": "按方案执行，可降低霉菌萌发率约85%、抑制虫害发生率约90%、延缓pH下降速率约60%，预计延长纸张寿命2-3倍。",
            "follow_up": "每季度一次微环境评估+pH复测；每年一次深度检视（春末秋初）；建立病害档案，连续监测5年可建立纸张老化速率基线。",
        }

    def get_herb_graph(self) -> Dict[str, Any]:
        nodes = []
        links = []
        node_ids = set()

        nodes.append({"id": "n_root", "label": "古籍病害与防蠹药方", "group": "core", "size": 30})

        for d in DISEASE_TYPES:
            nid = f"dis_{d}"
            nodes.append({"id": nid, "label": d, "group": "disease", "size": 18})
            links.append({"source": "n_root", "target": nid, "value": 3})
            node_ids.add(nid)

        for h in HERB_DATA:
            nid = f"herb_{h['id']}"
            nodes.append({
                "id": nid,
                "label": h["name"],
                "group": "herb",
                "size": 10 + 10 * (0.5 * h["efficacy_score"] + 0.3 * h["safety_score"] + 0.2 * h["aroma_score"]),
                "dynasty": h.get("dynasty", ""),
                "bencao_ref": h.get("bencao_ref", ""),
                "efficacy": h.get("efficacy", []),
            })
            for d in h["target_diseases"]:
                did = f"dis_{d}"
                if did in node_ids:
                    links.append({
                        "source": did,
                        "target": nid,
                        "value": 1 + h["efficacy_score"] * 3,
                    })

            for b in h["source_books"]:
                bid = f"book_{b}"
                if bid not in node_ids:
                    nodes.append({"id": bid, "label": b, "group": "book", "size": 14})
                    links.append({"source": "n_root", "target": bid, "value": 2})
                    node_ids.add(bid)
                links.append({
                    "source": bid,
                    "target": nid,
                    "value": 1.5,
                })

        return {"nodes": nodes, "links": links}


knowledge_graph = KnowledgeGraphService()
