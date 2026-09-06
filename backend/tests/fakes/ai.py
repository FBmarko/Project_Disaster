"""Deterministic stub/fake AI provider for automated unit and integration tests.

STRICTLY TEST-ONLY: Located outside the production `app/` package.
"""

from app.integrations.ai.base import PreparednessAIProvider
from app.integrations.ai.exceptions import (
    AIProviderError,
    AIProviderMalformedOutputError,
    AIProviderUnavailableError,
)
from app.schemas.ai import (
    PreparednessGuideContent,
    PreparednessGuideRequest,
    SupportedLanguage,
)


class StubPreparednessAIProvider(PreparednessAIProvider):
    """Configurable, offline, deterministic stub provider for automated testing."""

    def __init__(
        self,
        mode: str = "success",
        custom_content: PreparednessGuideContent | None = None,
    ) -> None:
        """Initialize the stub with a specific simulation mode."""
        self.mode = mode
        self.custom_content = custom_content
        self.last_request: PreparednessGuideRequest | None = None
        self.last_system_prompt: str | None = None
        self.last_user_context: str | None = None

    def generate_guide(
        self,
        request: PreparednessGuideRequest,
        system_prompt: str,
        user_context: str,
    ) -> PreparednessGuideContent:
        """Return deterministic test data or simulate configured failure modes."""
        self.last_request = request
        self.last_system_prompt = system_prompt
        self.last_user_context = user_context

        if self.mode == "unavailable":
            raise AIProviderUnavailableError(
                "Upstream AI service is currently unreachable."
            )
        elif self.mode == "malformed":
            raise AIProviderMalformedOutputError(
                "Upstream model returned JSON that failed schema validation."
            )
        elif self.mode == "error":
            raise AIProviderError("Upstream service encountered an unexpected error.")

        if self.custom_content is not None:
            return self.custom_content

        if request.language == SupportedLanguage.TR:
            return PreparednessGuideContent(
                summary=(
                    "Deprem hazırlığı bilinçli ve planlı adımlarla hayat kurtarır. "
                    "Evinizde tehlike avı yapın ve acil durum çantanızı hazır tutun."
                ),
                priorities=[
                    "Sarsıntı anında sağlam eşyanın yanında Çök-Kapan-Tutun yapın.",
                    "Pencerelerden ve devrilebilecek eşyalardan uzak durun.",
                    "Ağır mobilyaları ve beyaz eşyaları duvara sabitleyin.",
                ],
                emergency_kit=[
                    "Kişi başı en az 3 günlük içme suyu",
                    "Konserve ve dayanıklı gıdalar",
                    "İlk yardım çantası ve reçeteli ilaçlar",
                    "Pilli radyo ve yedek piller",
                    "El feneri ve düdük",
                ],
                communication_plan=[
                    "Şehir dışı acil durum irtibat kişisi belirleyin.",
                    "Aile bireyleriyle toplanma ve buluşma noktaları kararlaştırın.",
                    "Şebeke yoğunluğunu önlemek için iletişimi SMS ile sağlayın.",
                ],
                special_needs=[
                    "Çocuklar için kimlik kartı ve teselli eşyası hazırlayın.",
                    "Evcil hayvanlar için mama, su ve taşıma çantası bulundurun.",
                ],
                important_notes=[
                    "Afet anında yetkili kurumların resmi duyurularını takip edin.",
                    "Yetkililer izin vermeden hasarlı binalara kesinlikle girmeyin.",
                ],
            )
        else:
            return PreparednessGuideContent(
                summary=(
                    "Earthquake preparedness saves lives through structured planning. "
                    "Conduct a home hazard hunt and maintain an emergency kit."
                ),
                priorities=[
                    "Drop, Cover, and Hold On under sturdy furniture away from glass.",
                    "Stay away from windows, mirrors, and unanchored items.",
                    "Never use elevators or run to stairs during shaking.",
                ],
                emergency_kit=[
                    "At least 3-day supply of drinking water per person",
                    "Non-perishable food and manual can opener",
                    "First aid kit and essential prescription medications",
                    "Battery-powered radio and extra batteries",
                    "Flashlight and emergency whistle",
                ],
                communication_plan=[
                    "Designate an out-of-area emergency contact person.",
                    "Agree on household meeting locations inside/outside neighborhood.",
                    "Use text messaging instead of voice calls to keep networks clear.",
                ],
                special_needs=[
                    "Include identification, comfort items, and supplies for children.",
                    "Prepare pet carriers, food, water, and vaccination records.",
                ],
                important_notes=[
                    "Follow official announcements from AFAD and authorities.",
                    (
                        "Never re-enter damaged buildings until certified "
                        "safe by officials."
                    ),
                ],
            )
