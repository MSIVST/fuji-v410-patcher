#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TOOL_NAME = "Suzuki Garmin Fuji v4.10 patcher"
TOOL_VERSION = "2026.06.04"

GCD_MAGIC = b"GARMINd\x00"
HOST_REGION_TYPE = 0x02BD
SUPPORTED_HWID = 0x05BC
SUPPORTED_SWVER = 0x019A
SUPPORTED_HOST_SHA256 = "f566a42e1ea7a2cacd243e884a721209c024fb370635194f3c27b8b66928d3b6"

KNOWN_STOCK_GCD_SHA256 = {
    "NA": "257990a6cba54fdbf428c23ed07ae5a610b5c341b55005948c6f016028176756",
    "AU": "56fe3f19d74e314527613881e5ac81d102988672d3eb0a9de5caec74a7e626be",
    "EU": "31bc511f31aaf99b39bc56a6db0528fb40af693a25908af71830c9e70cdc5360",
    "IN": "48ed8cfc4e76643a1a017e8787e232522006c58029326ce243dd3eaf7e6b8e89",
    "RU": "15930479b7bfe69cb730976f3596a856aeb9b7ae1815898fc790f2a18dcc7d5a",
}

EXPECTED_FINAL_NA_SHA256 = "0f4531fb300e2ac03d13ab1cceb587aad24f2d8e847f1b640844d4e9c98cc901"


def attach_parent_console() -> bool:
    """Attach a windowed EXE back to PowerShell/CMD when one launched it."""
    if sys.platform != "win32":
        return sys.stdout is not None

    try:
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        attach_parent_process = -1
        already_attached_error = 5
        attached = bool(kernel32.AttachConsole(attach_parent_process))
        already_attached = ctypes.get_last_error() == already_attached_error
        if attached or already_attached:
            if sys.stdout is None:
                sys.stdout = open("CONOUT$", "w", encoding="utf-8", errors="replace", buffering=1)
            if sys.stderr is None:
                sys.stderr = open("CONOUT$", "w", encoding="utf-8", errors="replace", buffering=1)
            return True
    except Exception:
        pass

    return sys.stdout is not None


def configure_console_encoding() -> None:
    """Avoid localized Windows code pages crashing on Unicode paths."""
    if sys.stdout is None or sys.stderr is None:
        attach_parent_console()

    for stream in (sys.stdout, sys.stderr):
        if stream is None:
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(errors="replace")
            except Exception:
                pass


@dataclass
class ChecksumBlock:
    tlv_offset: int
    physical_start: int
    physical_end_exclusive: int
    additive_sum: int
    valid: bool


@dataclass
class ChunkInfo:
    tlv_header_offset: int
    file_data_offset: int
    size: int
    logical_start: int


@dataclass
class SectionInfo:
    descriptor_offset: int
    type_value: int
    attrs: dict[int, int]
    chunks: list[ChunkInfo] = field(default_factory=list)

    @property
    def logical_size(self) -> int:
        return sum(chunk.size for chunk in self.chunks)


@dataclass
class GcdLite:
    path: str
    size: int
    sha256: str
    magic_valid: bool
    checksum_blocks: list[ChecksumBlock]
    sections: list[SectionInfo]
    eof_offset: int


@dataclass
class PatchSpec:
    name: str
    fw_offset: int
    expected: bytes
    replacement: bytes
    description: str


@dataclass
class PhysicalPatchRange:
    patch_name: str
    fw_offset: int
    gcd_offset: int
    length: int
    before_hex: str
    after_hex: str
    status: str


@dataclass
class ChecksumRectifierChange:
    offset: int
    before: int
    after: int
    block_start: int
    block_end_exclusive: int


PATCHES = [
    PatchSpec(
        name="startup_warning_autonext",
        fw_offset=0x0027102E,
        expected=bytes.fromhex(
            "7E 48 40 69 00 28 AB D0 C7 F1 F3 FD 02 46 80 48 "
            "7B A1 00 68 D1 F1 CB F9"
        ),
        replacement=bytes.fromhex(
            "30 46 0A 21 FF F7 C5 FE 06 E0 "
            "00 BF 00 BF 00 BF 00 BF 00 BF 00 BF 00 BF"
        ),
        description="Immediately advances past the startup warning via the existing next-phase dispatcher.",
    ),
    PatchSpec(
        name="mp3_open_seek0",
        fw_offset=0x00778300,
        expected=bytes.fromhex("1E D0"),
        replacement=bytes.fromhex("C0 46"),
        description="Forces fresh MP3 open to use the existing backend seek path with 0 ms.",
    ),
    PatchSpec(
        name="map_reminder_interval_365d",
        fw_offset=0x00175C6C,
        expected=(28 * 24 * 60 * 60).to_bytes(4, "little"),
        replacement=(365 * 24 * 60 * 60).to_bytes(4, "little"),
        description="Changes map reminder snooze interval from 28 days to 365 days.",
    ),
    PatchSpec(
        name="map_reminder_text_1_year",
        fw_offset=0x00DBDC7C,
        expected="28 Days".encode("utf-16le") + b"\x00\x00",
        replacement="1 Year ".encode("utf-16le") + b"\x00\x00",
        description="Changes visible map reminder option text from '28 Days' to '1 Year'.",
    ),
]


def sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def checksum_bytes(blob: bytes) -> int:
    return sum(blob) & 0xFF


def hex0(value: int, width: int = 8) -> str:
    return f"0x{value:0{width}X}"


def read_tlv_header(data: bytes, offset: int) -> tuple[int, int]:
    header = struct.unpack_from("<I", data, offset)[0]
    return header & 0xFFFF, header >> 16


def parse_attrs(tlv6: bytes, tlv7: bytes) -> dict[int, int]:
    attrs: dict[int, int] = {}
    cursor = 0
    for offset in range(0, len(tlv6), 2):
        desc = struct.unpack_from("<H", tlv6, offset)[0]
        if desc == 0x5003:
            break
        attr_len = 1 << ((desc & 0xF000) >> 12)
        attrs[desc] = int.from_bytes(tlv7[cursor : cursor + attr_len], "little")
        cursor += attr_len
    return attrs


def parse_gcd(path: Path, blob: bytes) -> GcdLite:
    checksum_blocks: list[ChecksumBlock] = []
    sections: list[SectionInfo] = []
    cursor = 8
    previous_checksum_start = 0
    eof_offset = len(blob)
    magic_valid = blob.startswith(GCD_MAGIC)

    if not magic_valid:
        return GcdLite(
            path=str(path),
            size=len(blob),
            sha256=sha256_bytes(blob),
            magic_valid=False,
            checksum_blocks=[],
            sections=[],
            eof_offset=eof_offset,
        )

    while cursor + 4 <= len(blob):
        type_value, size_value = read_tlv_header(blob, cursor)
        if type_value == 0x0001:
            physical_end = cursor + 5
            additive_sum = checksum_bytes(blob[previous_checksum_start:physical_end])
            checksum_blocks.append(
                ChecksumBlock(
                    tlv_offset=cursor,
                    physical_start=previous_checksum_start,
                    physical_end_exclusive=physical_end,
                    additive_sum=additive_sum,
                    valid=additive_sum == 0,
                )
            )
            previous_checksum_start = physical_end
            cursor = physical_end
            continue

        if type_value == 0xFFFF:
            eof_offset = cursor
            break

        if type_value != 0x0006:
            cursor += 4 + size_value
            continue

        descriptor_offset = cursor
        cursor += 4
        tlv6 = blob[cursor : cursor + size_value]
        cursor += size_value

        type7, size7 = read_tlv_header(blob, cursor)
        if type7 != 0x0007:
            raise ValueError(f"Expected TLV 0x0007 at {hex0(cursor)}, got {hex0(type7, 4)}")
        cursor += 4
        tlv7 = blob[cursor : cursor + size7]
        cursor += size7

        attrs = parse_attrs(tlv6, tlv7)
        if 0x100A not in attrs:
            raise ValueError(f"Section without TYPE at {hex0(descriptor_offset)}")

        content_type = attrs[0x100A]
        logical_cursor = 0
        chunks: list[ChunkInfo] = []
        while cursor + 4 <= len(blob):
            current_type, current_size = read_tlv_header(blob, cursor)
            if current_type != content_type:
                break
            chunks.append(
                ChunkInfo(
                    tlv_header_offset=cursor,
                    file_data_offset=cursor + 4,
                    size=current_size,
                    logical_start=logical_cursor,
                )
            )
            logical_cursor += current_size
            cursor += 4 + current_size

        sections.append(
            SectionInfo(
                descriptor_offset=descriptor_offset,
                type_value=content_type,
                attrs=attrs,
                chunks=chunks,
            )
        )

    return GcdLite(
        path=str(path),
        size=len(blob),
        sha256=sha256_bytes(blob),
        magic_valid=magic_valid,
        checksum_blocks=checksum_blocks,
        sections=sections,
        eof_offset=eof_offset,
    )


def section_by_type(parsed: GcdLite, type_value: int) -> SectionInfo:
    matches = [section for section in parsed.sections if section.type_value == type_value]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one section {hex0(type_value, 4)}, found {len(matches)}")
    return matches[0]


def concat_section(blob: bytes, section: SectionInfo) -> bytes:
    return b"".join(
        blob[chunk.file_data_offset : chunk.file_data_offset + chunk.size]
        for chunk in section.chunks
    )


def iter_physical_ranges(section: SectionInfo, fw_offset: int, length: int) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    cursor = fw_offset
    remaining = length
    while remaining:
        match = None
        for chunk in section.chunks:
            start = chunk.logical_start
            end = start + chunk.size
            if start <= cursor < end:
                match = chunk
                break
        if match is None:
            raise ValueError(f"fw_all offset {hex0(cursor)} is not covered by section 0x02BD")
        in_chunk = cursor - match.logical_start
        take = min(remaining, match.size - in_chunk)
        ranges.append((match.file_data_offset + in_chunk, take))
        cursor += take
        remaining -= take
    return ranges


def read_fw_range(blob: bytes, section: SectionInfo, fw_offset: int, length: int) -> bytes:
    return b"".join(
        blob[gcd_offset : gcd_offset + take]
        for gcd_offset, take in iter_physical_ranges(section, fw_offset, length)
    )


def write_fw_range(blob: bytearray, section: SectionInfo, fw_offset: int, replacement: bytes) -> None:
    cursor = 0
    for gcd_offset, take in iter_physical_ranges(section, fw_offset, len(replacement)):
        blob[gcd_offset : gcd_offset + take] = replacement[cursor : cursor + take]
        cursor += take


def detect_region(sha256: str) -> str | None:
    for region, expected in KNOWN_STOCK_GCD_SHA256.items():
        if sha256.lower() == expected.lower():
            return region
    return None


def validate_base(parsed: GcdLite, blob: bytes, allow_unknown_hash: bool) -> tuple[str | None, SectionInfo, bytes]:
    if not parsed.magic_valid:
        raise ValueError("Input is not a Garmin GCD file; missing GARMINd magic.")
    if not parsed.checksum_blocks or not all(block.valid for block in parsed.checksum_blocks):
        raise ValueError("Input GCD checksum blocks are not valid. Refusing to patch.")

    region = detect_region(parsed.sha256)
    if region is None and not allow_unknown_hash:
        known = "\n".join(f"  {name}: {value}" for name, value in KNOWN_STOCK_GCD_SHA256.items())
        raise ValueError(
            "Input SHA-256 is not one of the known official v4.10 Suzuki Fuji GCDs.\n"
            f"Input SHA-256: {parsed.sha256}\n"
            "Known stock hashes:\n"
            f"{known}\n"
            "Use --allow-unknown-hash only if you know exactly what you are doing."
        )

    host = section_by_type(parsed, HOST_REGION_TYPE)
    host_hwid = host.attrs.get(0x1009)
    host_swver = host.attrs.get(0x100D)
    if host_hwid != SUPPORTED_HWID or host_swver != SUPPORTED_SWVER:
        raise ValueError(
            "Host firmware section is not the supported Suzuki Fuji v4.10 target: "
            f"hwid={hex0(host_hwid or 0, 4)}, swver={hex0(host_swver or 0, 4)}"
        )

    host_payload = concat_section(blob, host)
    host_hash = sha256_bytes(host_payload)
    if host_hash != SUPPORTED_HOST_SHA256:
        raise ValueError(
            "Host firmware payload is not the expected stock v4.10 fw_all.bin.\n"
            f"Expected host SHA-256: {SUPPORTED_HOST_SHA256}\n"
            f"Actual host SHA-256:   {host_hash}"
        )
    return region, host, host_payload


def apply_patch(blob: bytearray, host: SectionInfo, spec: PatchSpec) -> list[PhysicalPatchRange]:
    actual = read_fw_range(bytes(blob), host, spec.fw_offset, len(spec.expected))
    if actual == spec.replacement:
        return [
            PhysicalPatchRange(
                patch_name=spec.name,
                fw_offset=spec.fw_offset,
                gcd_offset=gcd_offset,
                length=take,
                before_hex=spec.replacement[cursor : cursor + take].hex(" "),
                after_hex=spec.replacement[cursor : cursor + take].hex(" "),
                status="already_patched",
            )
            for cursor, (gcd_offset, take) in zip(
                _cursors_for_ranges(iter_physical_ranges(host, spec.fw_offset, len(spec.replacement))),
                iter_physical_ranges(host, spec.fw_offset, len(spec.replacement)),
            )
        ]
    if actual != spec.expected:
        raise ValueError(
            f"Patch {spec.name} refused at fw_all {hex0(spec.fw_offset)}.\n"
            f"Expected: {spec.expected.hex(' ')}\n"
            f"Found:    {actual.hex(' ')}"
        )

    ranges: list[PhysicalPatchRange] = []
    cursor = 0
    physical = iter_physical_ranges(host, spec.fw_offset, len(spec.replacement))
    for gcd_offset, take in physical:
        before = bytes(blob[gcd_offset : gcd_offset + take])
        after = spec.replacement[cursor : cursor + take]
        blob[gcd_offset : gcd_offset + take] = after
        ranges.append(
            PhysicalPatchRange(
                patch_name=spec.name,
                fw_offset=spec.fw_offset + cursor,
                gcd_offset=gcd_offset,
                length=take,
                before_hex=before.hex(" "),
                after_hex=after.hex(" "),
                status="patched",
            )
        )
        cursor += take
    return ranges


def _cursors_for_ranges(ranges: list[tuple[int, int]]) -> list[int]:
    cursors: list[int] = []
    cursor = 0
    for _offset, take in ranges:
        cursors.append(cursor)
        cursor += take
    return cursors


def rectify_checksums(blob: bytearray, parsed: GcdLite) -> list[ChecksumRectifierChange]:
    changes: list[ChecksumRectifierChange] = []
    for block in parsed.checksum_blocks:
        current_sum = checksum_bytes(bytes(blob[block.physical_start : block.physical_end_exclusive]))
        if current_sum == 0:
            continue
        rectifier_offset = block.physical_end_exclusive - 1
        before = blob[rectifier_offset]
        blob[rectifier_offset] = (before - current_sum) & 0xFF
        changes.append(
            ChecksumRectifierChange(
                offset=rectifier_offset,
                before=before,
                after=blob[rectifier_offset],
                block_start=block.physical_start,
                block_end_exclusive=block.physical_end_exclusive,
            )
        )
    return changes


def verify_patched(parsed: GcdLite, blob: bytes) -> dict[str, Any]:
    host = section_by_type(parsed, HOST_REGION_TYPE)
    patch_checks = {}
    for spec in PATCHES:
        actual = read_fw_range(blob, host, spec.fw_offset, len(spec.replacement))
        patch_checks[spec.name] = actual == spec.replacement
    return {
        "magic_valid": parsed.magic_valid,
        "checksums_valid": all(block.valid for block in parsed.checksum_blocks),
        "section_types": [hex0(section.type_value, 4) for section in parsed.sections],
        "patches_present": patch_checks,
        "overall_patched_verification": parsed.magic_valid
        and all(block.valid for block in parsed.checksum_blocks)
        and all(patch_checks.values()),
    }


def dataclass_dict_with(row: Any, extra: dict[str, Any]) -> dict[str, Any]:
    output = asdict(row)
    output.update(extra)
    return output


def patch_gcd(input_path: Path, output_path: Path, allow_unknown_hash: bool, dry_run: bool) -> dict[str, Any]:
    input_blob = input_path.read_bytes()
    parsed = parse_gcd(input_path, input_blob)
    region, host, host_payload = validate_base(parsed, input_blob, allow_unknown_hash)

    patched_blob = bytearray(input_blob)
    patch_ranges: list[PhysicalPatchRange] = []
    for spec in PATCHES:
        patch_ranges.extend(apply_patch(patched_blob, host, spec))

    checksum_changes = rectify_checksums(patched_blob, parsed)
    patched_parsed = parse_gcd(output_path, bytes(patched_blob))
    verification = verify_patched(patched_parsed, bytes(patched_blob))

    report: dict[str, Any] = {
        "tool": TOOL_NAME,
        "tool_version": TOOL_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "input_file": str(input_path),
        "output_file": str(output_path),
        "dry_run": dry_run,
        "detected_region": region or "unknown",
        "input_size": len(input_blob),
        "output_size": len(patched_blob),
        "input_sha256": sha256_bytes(input_blob),
        "output_sha256": sha256_bytes(bytes(patched_blob)),
        "known_stock_region": region is not None,
        "host_sha256": sha256_bytes(host_payload),
        "patches": [
            {
                "name": spec.name,
                "fw_offset": hex0(spec.fw_offset),
                "description": spec.description,
                "expected_hex": spec.expected.hex(" "),
                "replacement_hex": spec.replacement.hex(" "),
            }
            for spec in PATCHES
        ],
        "physical_patch_ranges": [
            dataclass_dict_with(
                row,
                {
                "fw_offset_hex": hex0(row.fw_offset),
                "gcd_offset_hex": hex0(row.gcd_offset),
                },
            )
            for row in patch_ranges
        ],
        "checksum_rectifier_changes": [
            dataclass_dict_with(
                row,
                {
                "offset_hex": hex0(row.offset),
                "before_hex": hex0(row.before, 2),
                "after_hex": hex0(row.after, 2),
                "block_start_hex": hex0(row.block_start),
                "block_end_exclusive_hex": hex0(row.block_end_exclusive),
                },
            )
            for row in checksum_changes
        ],
        "verification": verification,
    }

    if not verification["overall_patched_verification"]:
        raise ValueError("Internal verification failed after patching; output was not written.")

    if not dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(patched_blob)

    return report


def default_output_path(input_path: Path) -> Path:
    return input_path.with_name(input_path.stem + "_patched_startup_mp3_map365" + input_path.suffix)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="FujiV410Patcher.exe",
        description=(
            "Patch an official Suzuki Garmin Fuji v4.10 GUPDATE.GCD. "
            "No Garmin firmware is included in this tool."
        ),
    )
    parser.add_argument("input_gcd", type=Path, help="Path to an official Suzuki Fuji v4.10 GUPDATE.GCD")
    parser.add_argument("-o", "--output", type=Path, help="Output patched GCD path")
    parser.add_argument("--report", type=Path, help="Optional JSON report path")
    parser.add_argument(
        "--allow-unknown-hash",
        action="store_true",
        help="Allow a GCD whose full-file SHA-256 is not in the known stock list, while still requiring the expected stock host payload.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Verify and simulate patching without writing the output GCD")
    parser.add_argument("--overwrite", action="store_true", help="Allow overwriting the output file")
    return parser


def print_usage() -> None:
    configure_console_encoding()
    parser = build_arg_parser()
    parser.print_help()
    print()
    print("Examples:")
    print("  FujiV410Patcher.exe GUPDATE.GCD --dry-run")
    print("  FujiV410Patcher.exe GUPDATE.GCD -o GUPDATE_patched.gcd")
    print("  FujiV410Patcher.exe GUPDATE.GCD -o GUPDATE_patched.gcd --report patch_report.json")


def main(argv: list[str] | None = None) -> int:
    configure_console_encoding()

    parser = build_arg_parser()
    args = parser.parse_args(argv)

    input_path = args.input_gcd
    if not input_path.exists():
        print(f"ERROR: input file does not exist: {input_path}", file=sys.stderr)
        return 2

    output_path = args.output or default_output_path(input_path)
    if output_path.exists() and not args.overwrite and not args.dry_run:
        print(f"ERROR: output file exists; use --overwrite or choose another path: {output_path}", file=sys.stderr)
        return 2

    try:
        report = patch_gcd(
            input_path=input_path,
            output_path=output_path,
            allow_unknown_hash=args.allow_unknown_hash,
            dry_run=args.dry_run,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"{TOOL_NAME} {TOOL_VERSION}")
    print(f"Input SHA-256:  {report['input_sha256']}")
    print(f"Output SHA-256: {report['output_sha256']}")
    print(f"Detected region: {report['detected_region']}")
    print(f"Verification: {report['verification']['overall_patched_verification']}")
    if args.dry_run:
        print("Dry run only; no output file written.")
    else:
        print(f"Wrote: {output_path}")
    if report["detected_region"] == "NA":
        print(f"Expected final NA SHA-256: {EXPECTED_FINAL_NA_SHA256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
