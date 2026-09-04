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
                    "Deprem öncesi, sırası ve sonrasında hazırlık hayat kurtarır. "
                    "Evinizde tehlike avı yapın ve çantanızı hazır tutun."
                ),
                before=[
                    "Ağır mobilyaları duvara sabitleyin.",
                    "Aile afet ve acil durum planı hazırlayın.",
                    "Acil durum çantasını hazır tutun.",
                ],
                during=[
                    "Sarsıntı anında sağlam bir eşyanın yanında Çök-Kapan-Tutun yapın.",
                    "Pencerelerden ve merdivenlerden uzak durun.",
                    "Asansörleri kesinlikle kullanmayın.",
                ],
                after=[
                    "Tesisatları (gaz, su, elektrik) vanalardan kapatın.",
                    "Acil durum çantanızı alarak binayı merdivenlerden tahliye edin.",
                    "Yetkililerin resmi duyurularını takip edin.",
                ],
                emergency_kit=[
                    "Kişi başı en az 3 günlük içme suyu",
                    "Konserve ve dayanıklı gıdalar",
                    "İlk yardım çantası ve reçeteli ilaçlar",
                    "Pilli radyo ve yedek piller",
                    "El feneri ve düdük",
                ],
                important_notes=[
                    "Yaşlı ve engelliler için özel ihtiyaçları planlayın.",
                    "Evcil hayvanlarınız için mama ve tasma hazırlayın.",
                ],
            )
        else:
            return PreparednessGuideContent(
                summary=(
                    "Preparedness before, during, and after an earthquake saves lives. "
                    "Conduct a home hazard hunt and maintain an emergency kit."
                ),
                before=[
                    "Secure heavy furniture and appliances to walls.",
                    "Establish a family emergency plan and meeting point.",
                    "Keep an emergency supply kit in an easily accessible location.",
                ],
                during=[
                    "Drop, Cover, and Hold On under sturdy furniture away from glass.",
                    "Stay away from windows, mirrors, and unanchored items.",
                    "Never use elevators during an earthquake.",
                ],
                after=[
                    "Safely shut off gas, water, and electricity at main valves.",
                    "Evacuate using stairs with your emergency kit; do not rush.",
                    "Monitor official emergency announcements and keep lines free.",
                ],
                emergency_kit=[
                    "At least 3-day supply of drinking water per person",
                    "Non-perishable food and manual can opener",
                    "First aid kit and essential prescription medications",
                    "Battery-powered radio and extra batteries",
                    "Flashlight and emergency whistle",
                ],
                important_notes=[
                    "Plan for specific needs of infants, elderly, or disabled persons.",
                    "Include pet food, water, and carriers in household preparations.",
                ],
            )
