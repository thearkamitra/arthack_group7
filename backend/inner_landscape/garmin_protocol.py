"""Shared BLE protocol, extracted from the verified research receiver."""
from typing import Any, Dict, List

HR_SERVICE_16 = "180d"
HR_SERVICE_128 = "0000180d-0000-1000-8000-00805f9b34fb"
HR_MEASUREMENT_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

def parse_hr_payload(data: bytearray) -> Dict[str, Any]:
    """Parses standard Bluetooth GATT Heart Rate Measurement Characteristic (0x2A37).

    Flags byte:
      Bit 0: Heart Rate Value Format (0 = UINT8, 1 = UINT16)
      Bit 1: Sensor Contact Status
      Bit 2: Sensor Contact Support
      Bit 3: Energy Expended Status (1 = UINT16 present)
      Bit 4: RR-Interval Status (1 = 1+ UINT16 present)
    """
    if not data or len(data) < 2:
        return {"error": "Invalid payload length"}

    flags = data[0]
    hr_format_uint16 = bool(flags & 0x01)
    contact_supported = bool(flags & 0x04)
    contact_detected = bool(flags & 0x02) if contact_supported else None
    energy_expended_present = bool(flags & 0x08)
    rr_present = bool(flags & 0x10)

    if hr_format_uint16:
        if len(data) < 3:
            return {"error": "Truncated 16-bit HR payload"}
        bpm = int.from_bytes(data[1:3], byteorder="little")
        offset = 3
    else:
        bpm = data[1]
        offset = 2

    energy_expended_kj = None
    if energy_expended_present:
        if offset + 2 > len(data):
            return {"error": "Truncated energy field"}
        energy_expended_kj = int.from_bytes(data[offset:offset + 2], byteorder="little")
        offset += 2

    rr_intervals_ms: List[float] = []
    if rr_present:
        if len(data) <= offset or (len(data) - offset) % 2:
            return {"error": "Truncated RR intervals"}
        while offset + 2 <= len(data):
            rr_raw = int.from_bytes(data[offset:offset + 2], byteorder="little")
            # 1/1024 second resolution to milliseconds
            rr_ms = (rr_raw / 1024.0) * 1000.0
            rr_intervals_ms.append(rr_ms)
            offset += 2

    return {
        "bpm": bpm,
        "contact_detected": contact_detected,
        "energy_expended_kj": energy_expended_kj,
        "rr_intervals_ms": rr_intervals_ms,
    }


def is_hr_match(device: Any, ad: Any) -> bool:
    """Matches HR service advertising in either 16-bit or 128-bit representation."""
    services = [s.lower() for s in (ad.service_uuids or [])]
    if any(s in (HR_SERVICE_16, HR_SERVICE_128) or s.startswith("0000180d") for s in services):
        return True
    name = (device.name or ad.local_name or "").lower()
    return "venu" in name or "garmin" in name

