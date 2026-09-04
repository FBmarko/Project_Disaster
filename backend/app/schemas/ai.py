"""Pydantic schemas and disclaimers for the AI disaster preparedness guide API."""

from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

DEFAULT_AI_DISCLAIMER_TR = (
    "Bu rehber yalnızca genel eğitim ve afet hazırlığı amacıyla yapay zeka desteğiyle "
    "üretilmiştir; afet tahmini yapmaz, resmi makamların yerini tutmaz ve hiçbir bina, "
    "güzergah veya toplanma alanının güvenliğini onaylamaz. Aktif bir acil durumda "
    "lütfen AFAD ve yetkili acil durum servislerinin resmi talimatlarını takip ediniz."
)

DEFAULT_AI_DISCLAIMER_EN = (
    "This guide is generated with AI support for general educational and preparedness "
    "purposes only; it does not predict disasters, replace official emergency "
    "authorities, or certify the safety of any building, route, or assembly area. "
    "In an active emergency, please strictly follow the official instructions of "
    "emergency services and competent authorities."
)


class DisasterType(StrEnum):
    """Supported disaster types for AI preparedness guidance."""

    EARTHQUAKE = "earthquake"
    FLOOD = "flood"
    FIRE = "fire"


class SupportedLanguage(StrEnum):
    """Supported output languages for AI preparedness guidance."""

    TR = "tr"
    EN = "en"


class PreparednessGuideRequest(BaseModel):
    """Client request model for generating a structured disaster preparedness guide.

    Strictly forbids extra fields to constrain user input, reduce the
    prompt-injection surface, and ensure predictable client integration.
    """

    model_config = ConfigDict(extra="forbid")

    disaster_type: DisasterType = Field(
        ...,
        description="Target disaster type for the preparedness guide",
        examples=["earthquake"],
    )
    city: str | None = Field(
        default=None,
        description=(
            "Optional geographic context (1-80 characters). Used strictly as plain "
            "contextual framing, not real-time conditions or hazard ratings."
        ),
        examples=["İstanbul"],
    )
    language: SupportedLanguage = Field(
        default=SupportedLanguage.TR,
        description="Output language for the guide and disclaimer ('tr' or 'en')",
        examples=["tr"],
    )

    @field_validator("city", mode="before")
    @classmethod
    def validate_city(cls, v: Any) -> str | None:
        """Strip whitespace and enforce 1-80 character bounds if provided."""
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("City must be a string if provided")
        stripped = v.strip()
        if not stripped:
            raise ValueError("City cannot be empty or whitespace-only when provided")
        if len(stripped) > 80:
            raise ValueError("City name must not exceed 80 characters")
        return stripped


# Strongly typed item definitions for bounded structured sections
SummaryText = Annotated[
    str,
    Field(
        min_length=10,
        max_length=600,
        description="Concise overview of preparedness principles for this scenario",
    ),
]
ActionItem = Annotated[
    str,
    Field(
        min_length=3,
        max_length=300,
        description="Specific actionable preparedness instruction",
    ),
]
KitItem = Annotated[
    str,
    Field(
        min_length=2,
        max_length=200,
        description="Essential emergency supply or household kit item",
    ),
]


class PreparednessGuideContent(BaseModel):
    """Structured preparedness guidance sections validated with bounded list lengths."""

    model_config = ConfigDict(extra="forbid")

    summary: SummaryText = Field(
        ...,
        examples=[
            "Deprem öncesi, sırası ve sonrasında bilinçli hazırlık hayat kurtarır. "
            "Evinizde tehlike avı yapın ve acil durum çantanızı hazır bulundurun."
        ],
    )
    before: list[ActionItem] = Field(
        ...,
        min_length=1,
        max_length=8,
        description="Preparation steps to take before an event occurs (1-8 items)",
        examples=[
            [
                "Ağır mobilyaları ve beyaz eşyaları duvara sabitleyin.",
                "Aile afet ve acil durum planı hazırlayın.",
                "Acil durum çantasını kolay erişilebilir bir yerde hazır tutun.",
            ]
        ],
    )
    during: list[ActionItem] = Field(
        ...,
        min_length=1,
        max_length=8,
        description="Protective actions to take during an active event (1-8 items)",
        examples=[
            [
                "Sarsıntı anında Çök-Kapan-Tutun hareketini uygulayın.",
                "Pencerelerden ve devrilebilecek ağır eşyalardan uzak durun.",
                "Asansörleri kesinlikle kullanmayın.",
            ]
        ],
    )
    after: list[ActionItem] = Field(
        ...,
        min_length=1,
        max_length=8,
        description="Safety precautions to observe after an event (1-8 items)",
        examples=[
            [
                "Doğal gaz, su ve elektrik vanalarını/şalterlerini kapatın.",
                "Acil durum çantanızı alarak binayı güvenli adımlarla tahliye edin.",
                "Resmi makamların uyarılarını ve duyurularını takip edin.",
            ]
        ],
    )
    emergency_kit: list[KitItem] = Field(
        ...,
        min_length=1,
        max_length=12,
        description="Recommended items for the emergency supply kit (1-12 items)",
        examples=[
            [
                "Kişi başı en az 3 günlük içme suyu",
                "Bozulmayan kuru ve konserve gıdalar",
                "İlk yardım seti ve reçeteli ilaçlar",
                "Pilli radyo ve yedek piller",
                "Düdük ve el feneri",
            ]
        ],
    )
    important_notes: list[ActionItem] = Field(
        default_factory=list,
        min_length=0,
        max_length=6,
        description=(
            "Accessibility considerations or vulnerable household member notes (0-6)"
        ),
        examples=[
            [
                "Engelli bireyler ve evcil hayvanlar için ihtiyaç planı yapın.",
                "Hatları meşgul etmemek için iletişimi SMS üzerinden sağlayın.",
            ]
        ],
    )


class PreparednessGuideResponse(BaseModel):
    """Complete public response payload for the AI disaster preparedness guide."""

    model_config = ConfigDict(extra="forbid")

    disaster_type: DisasterType = Field(
        ...,
        description="Disaster type addressed by this guide",
        examples=["earthquake"],
    )
    city: str | None = Field(
        default=None,
        description="Geographic context if supplied in request",
        examples=["İstanbul"],
    )
    language: SupportedLanguage = Field(
        ...,
        description="Response language ('tr' or 'en')",
        examples=["tr"],
    )
    generated_by_ai: bool = Field(
        default=True,
        description="Indicates that content was generated by an AI model",
    )
    guide: PreparednessGuideContent = Field(
        ...,
        description="Structured preparedness sections ready for UI rendering",
    )
    disclaimer: str = Field(
        ...,
        description="Backend-controlled legal and operational safety disclaimer",
        examples=[DEFAULT_AI_DISCLAIMER_TR],
    )
