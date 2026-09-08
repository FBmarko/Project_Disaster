import re

from app.integrations.ai.exceptions import AIOutputSafetyViolationError
from app.schemas.ai import (
    DisasterType,
    PreparednessGuideContent,
    PreparednessGuideRequest,
    SupportedLanguage,
)

# Deterministic disclaimers / cautions indicating safe, compliant statements
OUTPUT_SAFETY_DISCLAIMERS: tuple[re.Pattern[str], ...] = (
    re.compile(r"mümkün\s+değil", re.IGNORECASE),
    re.compile(r"bilin(?:emez|memektedir)", re.IGNORECASE),
    re.compile(r"tahmin\s+edilemez", re.IGNORECASE),
    re.compile(r"not\s+possible\s+to\s+predict", re.IGNORECASE),
    re.compile(r"cannot\s+be\s+predicted", re.IGNORECASE),
    re.compile(r"değerlendirmesi\s+gerekir", re.IGNORECASE),
    re.compile(r"requires\s+professional\s+evaluation", re.IGNORECASE),
    re.compile(r"resm[iî]\s+yönlendirmeleri", re.IGNORECASE),
    re.compile(r"follow\s+official", re.IGNORECASE),
)

# Deterministic prohibited patterns for post-generation output safety validation
PROHIBITED_OUTPUT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    # 1. Prediction (Turkish)
    (
        "PREDICTION_TR",
        re.compile(
            r"(?:\b(?:yarın|bu\s+(?:hafta|ay|yıl)|yakında|gelecek\s+(?:hafta|ay))\b.*"
            r"\b(?:deprem|afet|sarsıntı)\b.*\b(?:olacak|gerçekleşecek|meydana\s+gelecek|bekleniyor)\b)|"
            r"(?:\b(?:deprem|afet|sarsıntı)\b.*\b(?:kesinlikle|mutlaka)\b.*\b(?:olacak|gerçekleşecek|meydana\s+gelecek)\b)",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    # 2. Prediction (English)
    (
        "PREDICTION_EN",
        re.compile(
            r"(?:\b(?:an?\s+)?(?:earthquake|disaster)\b.*\bwill\s+(?:happen|occur|strike)\b.*\b(?:tomorrow|this\s+week|next\s+week|soon)\b)|"
            r"(?:\b(?:tomorrow|this\s+week|next\s+week)\b.*\b(?:an?\s+)?(?:earthquake|disaster)\b.*\bwill\s+(?:happen|occur|strike)\b)|"
            r"(?:\b(?:there\s+will\s+be|expect)\s+an?\s+earthquake\b.*\b(?:tomorrow|this\s+week|next\s+week)\b)",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    # 3. Future occurrence probability claim (Turkish & English)
    (
        "PROBABILITY_CLAIM",
        re.compile(
            r"(?:\b(?:deprem|afet|sarsıntı)\s+(?:olasılığı|ihtimali)\s*(?:[%]|yüzde)\s*\d+)|"
            r"(?:(?:[%]|yüzde)\s*\d+\s*(?:olasılıkla|ihtimalle)\s+(?:deprem|afet))|"
            r"(?:\b\d{1,3}%\s+(?:chance|probability|risk)\s+of\s+(?:an?\s+)?(?:earthquake|disaster)\b)|"
            r"(?:\b(?:chance|probability)\s+of\s+(?:an?\s+)?(?:earthquake|disaster)\s+(?:is\s+)?\d{1,3}%\b)",
            re.IGNORECASE,
        ),
    ),
    # 4. Building safety guarantee (Turkish & English)
    (
        "BUILDING_GUARANTEE",
        re.compile(
            r"(?:\b(?:bu\s+bina|bina(?:nız)?|ev(?:iniz)?|yapı(?:nız)?)\b.*?\b(?:kesinlikle\s+|tamamen\s+)?güvenlidir\b)|"
            r"(?:\b(?:this\s+building|your\s+building|this\s+structure|your\s+home|your\s+house)\b.*?\bis\s+(?:guaranteed\s+|completely\s+|totally\s+)?safe\b)|"
            r"(?:\bbuilding\s+is\s+safe\s+during\s+an?\s+earthquake\b)",
            re.IGNORECASE,
        ),
    ),
    # 5. Route safety guarantee (Turkish & English)
    (
        "ROUTE_GUARANTEE",
        re.compile(
            r"(?:\b(?:bu\s+rota|bu\s+güzergah|tahliye\s+(?:rotası|güzergahı))\b.*?\b(?:kesinlikle\s+|tamamen\s+|garantili\s+olarak\s+)?güvenlidir\b)|"
            r"(?:\b(?:this\s+route|this\s+path|this\s+evacuation\s+route)\b.*?\bis\s+(?:guaranteed\s+|completely\s+|totally\s+)?safe\b)|"
            r"(?:\bguaranteed?\s+safe\s+route\b)",
            re.IGNORECASE,
        ),
    ),
    # 6. Fabricated live warning (Turkish & English)
    (
        "LIVE_WARNING",
        re.compile(
            r"(?:\bAFAD\s+(?:şu\s+anda|anlık\s+olarak|derhal|az\s+önce)\s+.*(?:tahliye\s+emri\s+verdi|uyarı\s+yayınladı|alarm\s+verdi))|"
            r"(?:\bAFAD\s+tahliye\s+emri\s+verdi\b)|"
            r"(?:\bAFAD\s+(?:has\s+)?(?:just\s+)?(?:issued|declared)\s+an?\s+(?:immediate\s+)?(?:evacuation\s+order|emergency\s+alert)\b)|"
            r"(?:\bevacuation\s+order\s+has\s+(?:just\s+)?been\s+issued\s+by\s+AFAD\b)",
            re.IGNORECASE,
        ),
    ),
    # 7. False authority (Turkish & English)
    (
        "FALSE_AUTHORITY",
        re.compile(
            r"(?:\b(?:ben|biz)\s+(?:bir\s+)?AFAD\s+(?:yetkilisiyiz|yetkilisiyim|görevlisiyim|temsilcisiyim)\b)|"
            r"(?:\bAFAD\s+olarak\s+(?:sizlere\s+)?(?:bildiririz|talimat\s+veriyoruz|emrediyoruz)\b)|"
            r"(?:\b(?:i\s+am|we\s+are)\s+(?:an?\s+)?(?:AFAD\s+official|emergency\s+authority|government\s+official)\b)|"
            r"(?:\bas\s+AFAD,\s+we\s+(?:order|instruct|declare)\b)",
            re.IGNORECASE,
        ),
    ),
)


class PreparednessSafetyPolicy:
    """Encapsulates safety constraints and prompts for AI preparedness generation."""

    PROHIBITED_BEHAVIORS_EN: tuple[str, ...] = (
        "Never predict specific future earthquakes, floods, fires, or disasters.",
        "Never state probabilities, dates, or times for future disaster occurrences.",
        "Never claim any specific building or structure is safe or unsafe.",
        "Never claim an evacuation route or path is safe or open.",
        (
            "Never claim an assembly area is officially certified without verified "
            "source data."
        ),
        "Never invent emergency alerts, alarms, sirens, or official evacuation orders.",
        (
            "Never claim or imply real-time sensor, weather, or emergency condition "
            "knowledge."
        ),
        "Never impersonate AFAD, the government, or any emergency services authority.",
        "Never diagnose medical conditions or diseases.",
        ("Never prescribe medication, treatments, or individualized medical plans."),
        (
            "Never claim professional medical authority or discourage contacting "
            "emergency/medical professionals."
        ),
        (
            "Never blur temporal phases; do not instruct evacuation or running to "
            "stairs/exits while earthquake shaking is actively occurring."
        ),
        (
            "Never invent or assert current local conditions (road closures, "
            "evacuation orders, fire spread, weather); always defer situational "
            "decisions to official authorities."
        ),
    )

    PROHIBITED_BEHAVIORS_TR: tuple[str, ...] = (
        "Gelecekteki afetler için kesinlikle zaman veya tarih tahmini yapmayın.",
        "Afet olasılığı, olasılık veya belirli tarih/saat iddialarında bulunmayın.",
        "Herhangi bir binanın veya yapının güvenli ya da güvensiz olduğunu söylemeyin.",
        "Herhangi bir tahliye güzergahının kesin olarak güvenli olduğunu söylemeyin.",
        (
            "Doğrulanmış veri olmadan toplanma alanı veya toplanma alanlarının resmi "
            "onaylı olduğunu söylemeyin."
        ),
        "Acil durum alarmları, sirenleri veya resmi tahliye emirleri uydurmayın.",
        (
            "Canlı sensör, hava durumu veya anlık acil durum bilgisine sahip "
            "olduğunuzu söylemeyin."
        ),
        "Kendinizi AFAD veya resmi acil durum servisi yetkilisi olarak tanıtmayın.",
        "Tıbbi durum, hastalık veya yaralanma teşhisi koymayın.",
        ("İlaç reçete etmeyin veya kişiye özel tıbbi tedavi planları sunmayın."),
        (
            "Profesyonel tıbbi otorite iddia etmeyin; acil servislere veya sağlık "
            "personeline başvurmayı engelleyici tavsiyelerde bulunmayın."
        ),
        (
            "Zaman fazlarını karıştırmayın; aktif sarsıntı sürerken merdivenlere "
            "veya çıkışlara koşmayı, sarsıntı anında tahliyeyi tavsiye etmeyin."
        ),
        (
            "Anlık yerel koşulları (tahliye emirleri, yol durumu, yangın yayılımı, "
            "hava durumu) uydurmayın; durumsal kararları daima resmi makamlara bırakın."
        ),
    )

    PERMITTED_SCOPE_EN: tuple[str, ...] = (
        "General educational preparation before a disaster occurs.",
        "Standard protective actions during an event (e.g., Drop-Cover-Hold On).",
        "Immediate precautions following an event (utilities shutoff, safe exit).",
        "Essential items and checklists for family emergency supply kits.",
        "Household emergency planning and out-of-area communication strategies.",
        (
            "Accessibility considerations for children, older adults, people with "
            "disabilities, and pets."
        ),
        (
            "Basic general emergency guidance: checking for injuries, calling 112 "
            "emergency services, keeping a basic first-aid kit, following trained "
            "personnel, and general low-risk protective actions."
        ),
        (
            "Chronological phase-appropriate guidance (before: mitigation/planning, "
            "during: immediate life protection, after: safe recovery)."
        ),
        (
            "Deference to verified official instructions from AFAD and emergency "
            "authorities for all situational decisions."
        ),
    )

    PERMITTED_SCOPE_TR: tuple[str, ...] = (
        "Afet öncesinde alınacak genel ve eğitsel hazırlık tedbirleri.",
        "Afet anında uygulanacak standart koruyucu eylemler (örn. Çök-Kapan-Tutun).",
        "Afet sonrasında alınacak temel önlemler (tesisat kapatma, güvenli tahliye).",
        "Aile acil durum çantası ve temel ihtiyaç malzemeleri önerileri.",
        "Aile afet planı ve şehir dışı acil durum irtibat kişisi belirleme.",
        (
            "Çocuklar, yaşlılar, engelliler ve evcil hayvanlar için erişilebilirlik "
            "ve özel ihtiyaç uyarıları."
        ),
        (
            "Temel genel acil durum rehberliği: yaralanma kontrolü, 112 acil "
            "servis yönlendirmesi, temel ilk yardım çantası bulundurma, eğitimli "
            "ekipleri takip etme ve düşük riskli koruyucu eylemler."
        ),
        (
            "Kronolojik zaman fazlarına uygun rehberlik (öncesi: hazırlık/önlem, "
            "sırası: can güvenliğini koruma, sonrası: güvenli toparlanma)."
        ),
        (
            "Durumsal kararlarda AFAD ve resmi acil durum makamlarının talimatlarına "
            "yönlendirme."
        ),
    )

    DISASTER_DOMAINS_EN: dict[DisasterType, str] = {
        DisasterType.EARTHQUAKE: (
            "Before: Household preparedness, family communication planning, and "
            "anchoring heavy furniture away from beds and exits. "
            "During active shaking: Practice Drop, Cover, and Hold On under sturdy "
            "furniture away from windows; strictly do NOT run toward stairs, exits, "
            "or balconies, and do NOT use elevators or attempt evacuation while "
            "shaking is actively occurring. "
            "After shaking has stopped: Check for injuries and hazards; only if safe "
            "and appropriate, shut off utilities without touching damaged equipment; "
            "evacuate calmly using stairs if necessary; follow instructions from "
            "official emergency authorities without assuming building safety or "
            "blanket rules."
        ),
        DisasterType.FLOOD: (
            "Before: Understand local flood risk, move essential documents and "
            "belongings to upper levels, and prepare family emergency supplies. "
            "During flood conditions: Strictly do not walk or wade into moving "
            "floodwater; strictly do not drive through water-covered roads or "
            "underpasses; avoid electrical hazards, submerged wiring, and downed "
            "power lines; move to higher ground away from flood-prone low areas "
            "when appropriate and safe. "
            "After flooding: Avoid entering flood-damaged structures or standing "
            "water until permitted; follow verified instructions from official "
            "emergency authorities."
        ),
        DisasterType.FIRE: (
            "Before: Household fire prevention, smoke alarm testing, and planning two "
            "unobstructed escape routes for every room. "
            "During a fire: Immediate safe evacuation is the primary objective; crawl "
            "low under smoke to escape toxic gases; check closed doors for heat with "
            "the back of the hand; call 112/emergency services immediately once "
            "outside; attempting to fight a fire is NOT expected—fire extinguishers "
            "are purely conditional for very small, contained fires when safe and an "
            "escape route is clear. "
            "After evacuation: Strictly never re-enter a burning or fire-damaged "
            "structure until emergency personnel explicitly declare it safe; follow "
            "official responders."
        ),
    }

    DISASTER_DOMAINS_TR: dict[DisasterType, str] = {
        DisasterType.EARTHQUAKE: (
            "Öncesinde: Ev hazırlığı, aile afet planı ve ağır eşyaların güvenli "
            "noktalara sabitlenmesi. "
            "Sarsıntı anında: Sağlam bir eşyanın yanında Çök-Kapan-Tutun pozisyonu "
            "alarak pencerelerden ve devrilebilecek eşyalardan korunma; sarsıntı "
            "sürerken kesinlikle merdivenlere, çıkışlara veya balkonlara koşmama, "
            "asansörleri kullanmama ve sarsıntı anında tahliyeye kalkışmama. "
            "Sarsıntı tamamen durduktan sonra: Yaralanma ve tehlike kontrolü yapma; "
            "yalnızca güvenli ve uygunsa hasarlı ekipmana dokunmadan vanaları ve "
            "şalterleri kapatma; gerekirse merdivenleri kullanarak sakin tahliye ve "
            "resmi makamların talimatlarına uyma (bina yapısal güvenliği veya "
            "zorunlu tahliye iddiasında bulunmama)."
        ),
        DisasterType.FLOOD: (
            "Öncesinde: Yerel sel riskini tanıma, önemli evrak ve eşyaları üst "
            "katlara taşıma ve acil durum malzemelerini hazırlama. "
            "Sel anında: Akan sel sularına kesinlikle girmeme veya yürümeme; suyla "
            "kaplı yollara, alt geçitlere araçla kesinlikle girmeme; sel suları "
            "yakınındaki elektrik hatlarından ve suya batmış prizlerden uzak durma; "
            "uygun ve güvenli olduğunda çukur alanlardan yüksek güvenli bölgelere "
            "geçme. "
            "Sel sonrasında: Yetkililer izin verene kadar hasarlı binalara veya "
            "durgun sel sularına girmeme; doğrulanmış resmi makam ve AFAD "
            "uyarılarını takip etme."
        ),
        DisasterType.FIRE: (
            "Öncesinde: Ev yangın tedbirleri, duman dedektörü kontrolü ve her oda için "
            "engelsiz iki farklı tahliye çıkış rotası planlama. "
            "Yangın anında: Öncelik her zaman derhal ve güvenli tahliyedir; zehirli "
            "gazlardan korunmak için duman altında çömelerek ilerleme; kapıları "
            "açmadan önce elin tersiyle sıcaklık kontrolü yapma; güvenli bir noktaya "
            "çıkar çıkmaz 112 acil servisi arama; yangınla mücadele etmek kesinlikle "
            "bir zorunluluk veya öncelik değildir—yangın tüpü yalnızca yangın çok "
            "küçük, kontrol edilebilir ve kaçış yolu açıksa isteğe bağlı olarak "
            "kullanılabilir. "
            "Tahliye sonrasında: İtfaiye ve resmi yetkililer izin vermeden yanan "
            "binaya kesinlikle tekrar girmeme; eğitimli müdahale ekiplerinin "
            "talimatlarına uyma."
        ),
    }

    @classmethod
    def build_system_prompt(cls, language: SupportedLanguage) -> str:
        """Build the non-negotiable system prompt enforcing safety and schema."""
        if language == SupportedLanguage.TR:
            prohibitions = "\n".join(f"- {p}" for p in cls.PROHIBITED_BEHAVIORS_TR)
            permitted = "\n".join(f"- {p}" for p in cls.PERMITTED_SCOPE_TR)
            lang_instruction = "Yanıtınızı kesinlikle Türkçe olarak hazırlayın."
            section_guidance = (
                "BÖLÜM KURALLARI VE TERCİH EDİLEN MADDE SAYILARI (ZORUNLU):\n"
                "- 'summary': 2-3 kısa ve öz cümle ile genel özet (10-600 karakter).\n"
                "- 'priorities': En kritik can güvenliği ve hazırlık öncelikleri "
                "(3-5 madde; her madde tek bir kısa, net cümle olmalıdır; "
                "tercih edilen 5 maddeyi aşmayın).\n"
                "- 'emergency_kit': Acil durum çantası ve temel ihtiyaç "
                "malzemeleri (5-8 madde; kısa ve net madde adları; "
                "tercih edilen 8 maddeyi aşmayın).\n"
                "- 'communication_plan': Aile ve hane halkı acil durum iletişim "
                "planı (3-5 net madde; toplanma noktası, şehir dışı irtibat kişisi, "
                "SMS kullanımı vb.; tercih edilen 5 maddeyi aşmayın).\n"
                "- 'special_needs': Çocuk, yaşlı birey veya evcil hayvan gibi "
                "belirtilen hane özelliklerine yönelik hazırlık adımları (0-4 "
                "madde; özel durum belirtilmemişse genel erişilebilirlik/bireysel "
                "ihtiyaç tavsiyeleri; tercih edilen 4 maddeyi aşmayın).\n"
                "- 'important_notes': Resmi makamlara (AFAD) yönlendirme, kritik "
                "güvenlik uyarıları ve hatırlatmalar (2-4 kısa madde; tercih edilen "
                "4 maddeyi aşmayın).\n"
                "Her madde tek bir kısa cümle veya kısa bir ifade olmalıdır. "
                "Belirtilen tercih edilen madde sayılarını aşmayın. Bölümler "
                "arasında aynı tavsiyeleri tekrarlamaktan, giriş ve dolgu "
                "ifadelerinden kesinlikle kaçının. Doğrudan ve net olun.\n\n"
            )
        else:
            prohibitions = "\n".join(f"- {p}" for p in cls.PROHIBITED_BEHAVIORS_EN)
            permitted = "\n".join(f"- {p}" for p in cls.PERMITTED_SCOPE_EN)
            lang_instruction = "Prepare your response strictly in English."
            section_guidance = (
                "SECTION REQUIREMENTS & PREFERRED CONCISE COUNTS (MANDATORY):\n"
                "- 'summary': 2-3 concise sentences providing overview "
                "(10-600 characters).\n"
                "- 'priorities': Most critical immediate life-safety actions "
                "and essential preparations (3-5 items; each item a single short, "
                "direct sentence; do not exceed 5 items).\n"
                "- 'emergency_kit': Recommended emergency kit items tailored to "
                "household needs and size (5-8 items; short concise item names; "
                "do not exceed 8 items).\n"
                "- 'communication_plan': Family and household emergency "
                "communication strategy (3-5 items; out-of-area contact, meeting "
                "points, SMS over voice; do not exceed 5 items).\n"
                "- 'special_needs': Household-specific considerations for "
                "children, elderly members, or pets (0-4 items; if none, "
                "general accessibility/individual guidance; do not exceed 4 items).\n"
                "- 'important_notes': Caveats, official emergency source "
                "reminders (AFAD), and essential boundaries (2-4 items; "
                "do not exceed 4 items).\n"
                "Each item must normally be one short sentence or phrase. "
                "Do not exceed these preferred counts. Avoid repeating the same advice "
                "across sections, and avoid introductory or filler prose. "
                "Be direct and concise.\n\n"
            )

        return (
            "You are an expert, calm, and safety-conscious disaster preparedness "
            "assistant for the AFET360 platform.\n"
            f"{lang_instruction}\n\n"
            "MANDATORY SAFETY POLICY & STRICT PROHIBITIONS:\n"
            f"{prohibitions}\n\n"
            "PERMITTED EDUCATIONAL PREPAREDNESS SCOPE:\n"
            f"{permitted}\n\n"
            f"{section_guidance}"
            "OUTPUT FORMAT REQUIREMENTS:\n"
            "You must return ONLY valid JSON matching this schema:\n"
            "{\n"
            '  "summary": "10-600 characters overview",\n'
            '  "priorities": ["1 to 8 critical priorities and actions"],\n'
            '  "emergency_kit": ["1 to 12 essential kit items"],\n'
            '  "communication_plan": ["1 to 8 family communication steps"],\n'
            '  "special_needs": ["0 to 8 notes for children, elderly, or pets"],\n'
            '  "important_notes": ["0 to 6 caveats and official source reminders"]\n'
            "}\n"
            "Do NOT include Markdown formatting or text outside the JSON object."
        )

    @classmethod
    def build_user_context(cls, request: PreparednessGuideRequest) -> str:
        """Construct user context to reduce prompt-injection surface."""
        lang = request.language
        disaster_type = request.disaster_type
        domain_guidance = (
            cls.DISASTER_DOMAINS_TR.get(disaster_type, "")
            if lang == SupportedLanguage.TR
            else cls.DISASTER_DOMAINS_EN.get(disaster_type, "")
        )

        if request.city:
            city_clause = (
                f"Geographic Context: {request.city} (Plain geographic context only. "
                "Do NOT claim local real-time knowledge or building safety).\n"
            )
        else:
            city_clause = "Geographic Context: None specified (General guidance).\n"

        children_val = "Yes" if request.has_children else "No"
        elderly_val = "Yes" if request.has_elderly_person else "No"
        pets_val = "Yes" if request.has_pets else "No"

        household_clause = (
            "HOUSEHOLD CONTEXT:\n"
            f"- Household size: {request.household_size} person(s)\n"
            f"- Children in household: {children_val}\n"
            f"- Elderly person in household: {elderly_val}\n"
            f"- Pets in household: {pets_val}\n"
            "- Personalization rules: Scale emergency kit quantities reasonably "
            f"for {request.household_size} person(s). "
            "Address children, elderly members, and pets in 'special_needs' and "
            "kit items only as indicated above. Do NOT fabricate specific ages, "
            "medical conditions, diagnoses, prescription drug names, or pet "
            "species.\n"
        )

        return (
            f"DISASTER TYPE: {disaster_type.value.upper()}\n"
            f"{city_clause}"
            f"{household_clause}"
            f"SPECIFIC DOMAIN FOCUS:\n{domain_guidance}\n\n"
            "Generate practical, step-by-step educational guidance matching the "
            "required JSON structure exactly. Do not output anything outside JSON."
        )

    @classmethod
    def collect_all_text_segments(cls, content: PreparednessGuideContent) -> list[str]:
        """Extract all visible generated text segments across all six sections."""
        segments: list[str] = [content.summary]
        for section in (
            content.priorities,
            content.emergency_kit,
            content.communication_plan,
            content.special_needs,
            content.important_notes,
        ):
            segments.extend(section)
        return segments

    @classmethod
    def validate_output_safety(cls, content: PreparednessGuideContent) -> None:
        """Validate generated preparedness guide content against safety rules.

        Inspects all generated text segments across all six sections.
        Sentence-level splitting ensures disclaimers in one sentence do not
        mask prohibited claims in another sentence.

        Raises:
            AIOutputSafetyViolationError: If any prohibited semantic claim is detected.
        """
        segments = cls.collect_all_text_segments(content)
        for segment in segments:
            sentences = [s.strip() for s in re.split(r"[.!?\n]+", segment) if s.strip()]
            for sentence in sentences:
                has_disclaimer = any(
                    disc.search(sentence) for disc in OUTPUT_SAFETY_DISCLAIMERS
                )
                if has_disclaimer:
                    continue

                for violation_name, pattern in PROHIBITED_OUTPUT_PATTERNS:
                    if pattern.search(sentence):
                        raise AIOutputSafetyViolationError(
                            f"Prohibited AI output claim detected: {violation_name}"
                        )
