"""Shared entity classes for the Wilma integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_SERVER_URL, CONF_USERNAME, DOMAIN
from .coordinator import StudentData, WilmaConfigEntry, WilmaCoordinator


def student_key(student: StudentData) -> str:
    """Stable identifier of a student within an account, used in unique IDs."""
    return str(student.primus_id) if student.primus_id else student.user_id.lstrip("!")


def account_device_info(entry: WilmaConfigEntry) -> DeviceInfo:
    """The device for account-level entities."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"Wilma ({entry.data.get(CONF_USERNAME)})",
        manufacturer="Visma",
        model="Wilma",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=entry.data.get(CONF_SERVER_URL),
    )


class WilmaAccountEntity(CoordinatorEntity[WilmaCoordinator]):
    """An entity describing the account or the integration itself."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: WilmaCoordinator, entry: WilmaConfigEntry, key: str
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = account_device_info(entry)


class WilmaStudentEntity(CoordinatorEntity[WilmaCoordinator]):
    """An entity describing one student; each student has their own device."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WilmaCoordinator,
        entry: WilmaConfigEntry,
        student: StudentData,
        key: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._user_id = student.user_id
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.entry_id}_{student_key(student)}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{student_key(student)}")},
            name=f"Wilma {student.first_name}",
            manufacturer="Visma",
            model="Wilma student",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=entry.data.get(CONF_SERVER_URL),
        )

    @property
    def student(self) -> StudentData | None:
        """This entity's student's current data."""
        data = self.coordinator.data
        return data.students.get(self._user_id) if data else None

    @property
    def available(self) -> bool:
        """Available while the coordinator works and the student is still listed."""
        return super().available and self.student is not None
