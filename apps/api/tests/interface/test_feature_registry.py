"""The configured premium-feature catalog maps into the domain registry."""

from frontdesk.core.settings import Settings
from frontdesk.domain.ids import FeatureKey
from frontdesk.interface.app import feature_registry_from

VOICE = FeatureKey("voice_receptionist")


def test_default_settings_ship_the_voice_catalog_and_demo_numbers() -> None:
    settings = Settings()

    keys = [feature.key for feature in settings.premium_features]
    assert "voice_receptionist" in keys
    languages = {number.language for number in settings.voice_demo_numbers}
    assert languages == {"en", "ru", "es"}  # a demo number per supported language


def test_feature_registry_from_config_maps_keys_and_display_copy() -> None:
    registry = feature_registry_from(Settings().premium_features)

    voice = registry.require(VOICE)
    assert voice.name == "Voice receptionist"
    assert voice.pricing == "$1 per call"
