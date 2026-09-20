#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fuji_v410_delta_v36 as delta_v36


TOOL_NAME = "Suzuki Garmin Fuji v4.10 patcher"
TOOL_VERSION = "1.2.0"
PROJECT_URL = "https://github.com/MSIVST/fuji-v410-patcher"

PATCH_SET_HELP = (
    "This patch set updates stock Fuji v4.10 with:\n\n"
    "• Ogg/Vorbis playback, while safely skipping surround-sound files.\n"
    "• WMA cover art and safe rejection of WMA formats the unit cannot play.\n"
    "• Progressive JPEG cover art.\n"
    "• JPEG album art in supported ID3v2.3/v2.4 MP3 files (PNG is not supported).\n"
    "• Automatic startup-warning advance.\n"
    "• MP3 playback that does not end early when a track opens.\n"
    "• A one-year map-reminder option.\n\n"
    "The fixes are installed together. The patcher checks the stock firmware "
    "before and after patching."
)

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

# The patched host payload is identical for every 4.10 region, so a single
# constant replaces what would otherwise be five per-region final GCD hashes.
EXPECTED_PATCHED_HOST_SHA256 = delta_v36.PATCHED_HOST_SHA256

if delta_v36.STOCK_HOST_SHA256 != SUPPORTED_HOST_SHA256:
    raise RuntimeError(
        "Embedded delta was generated against a different stock payload."
    )


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


DELTA: list[tuple[int, bytes]] = delta_v36.load_delta()


@dataclass
class FeatureCheck:
    """A representative site used for the human-readable report.

    Correctness is bounded by the payload hashes, not by these checks; they
    exist so the report and GUI can name what was applied.
    """

    name: str
    fw_offset: int
    expected: bytes
    description: str


def _feature_checks() -> list[FeatureCheck]:
    checks: list[FeatureCheck] = []
    for name, offset, description in delta_v36.FEATURES:
        for start, payload in DELTA:
            if start <= offset < start + len(payload):
                cursor = offset - start
                take = min(8, len(payload) - cursor)
                checks.append(
                    FeatureCheck(
                        name=name,
                        fw_offset=offset,
                        expected=payload[cursor : cursor + take],
                        description=description,
                    )
                )
                break
        else:
            raise RuntimeError(f"feature site {hex(offset)} missing from delta")
    return checks


FEATURES: list[FeatureCheck] = _feature_checks()


def sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_path(path: Path) -> str:
    try:
        resolved = path.resolve(strict=False)
    except OSError:
        resolved = Path(os.path.abspath(str(path)))
    return os.path.normcase(str(resolved))


def paths_alias(first: Path, second: Path) -> bool:
    """Return whether two paths identify the same file or destination."""
    try:
        if first.samefile(second):
            return True
    except (FileNotFoundError, OSError):
        pass
    return _canonical_path(first) == _canonical_path(second)


def require_distinct_paths(paths: list[tuple[str, Path]]) -> None:
    for index, (first_name, first_path) in enumerate(paths):
        for second_name, second_path in paths[index + 1 :]:
            if paths_alias(first_path, second_path):
                raise ValueError(
                    f"Unsafe path alias: {first_name} and {second_name} identify "
                    f"the same destination ({first_path})."
                )


def atomic_write_bytes(path: Path, payload: bytes, overwrite: bool = False) -> None:
    """Durably stage bytes beside path, then atomically publish the file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Destination already exists: {path}")

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())

        if overwrite:
            os.replace(str(temporary), str(path))
        elif os.name == "nt":
            os.rename(str(temporary), str(path))
        else:
            os.link(str(temporary), str(path))
            temporary.unlink()

        if path.stat().st_size != len(payload) or sha256_file(path) != sha256_bytes(payload):
            raise OSError(f"Post-write verification failed: {path}")
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_write_text(path: Path, text: str, overwrite: bool = False) -> None:
    atomic_write_bytes(path, text.encode("utf-8"), overwrite=overwrite)


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


def validate_base(parsed: GcdLite, blob: bytes) -> tuple[str, SectionInfo, bytes]:
    if not parsed.magic_valid:
        raise ValueError("Input is not a Garmin GCD file; missing GARMINd magic.")
    if not parsed.checksum_blocks or not all(block.valid for block in parsed.checksum_blocks):
        raise ValueError("Input GCD checksum blocks are not valid. Refusing to patch.")

    region = detect_region(parsed.sha256)
    if region is None:
        known = "\n".join(f"  {name}: {value}" for name, value in KNOWN_STOCK_GCD_SHA256.items())
        raise ValueError(
            "Input SHA-256 is not one of the known official v4.10 Suzuki Fuji GCDs.\n"
            f"Input SHA-256: {parsed.sha256}\n"
            "Known stock hashes:\n"
            f"{known}"
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


def apply_delta(blob: bytearray, host: SectionInfo) -> tuple[int, int]:
    """Write every delta span into the host section. Returns (spans, bytes).

    The stock payload hash is validated before this runs, so each span's prior
    contents are already known exactly; the patched payload hash is validated
    afterwards. That pair bounds the transformation more tightly than
    per-span before/after comparisons could.
    """
    written = 0
    for fw_offset, payload in DELTA:
        cursor = 0
        for gcd_offset, take in iter_physical_ranges(host, fw_offset, len(payload)):
            blob[gcd_offset : gcd_offset + take] = payload[cursor : cursor + take]
            cursor += take
        if cursor != len(payload):
            raise ValueError(f"Short write at fw_all {hex0(fw_offset)}.")
        written += len(payload)
    return len(DELTA), written


def verify_patched(parsed: GcdLite, blob: bytes) -> dict[str, Any]:
    host = section_by_type(parsed, HOST_REGION_TYPE)
    patch_checks = {}
    for check in FEATURES:
        actual = read_fw_range(blob, host, check.fw_offset, len(check.expected))
        patch_checks[check.name] = actual == check.expected
    host_hash = sha256_bytes(concat_section(blob, host))
    host_hash_ok = host_hash == EXPECTED_PATCHED_HOST_SHA256
    return {
        "magic_valid": parsed.magic_valid,
        "checksums_valid": all(block.valid for block in parsed.checksum_blocks),
        "section_types": [hex0(section.type_value, 4) for section in parsed.sections],
        "patched_host_sha256": host_hash,
        "patched_host_sha256_matches": host_hash_ok,
        "patches_present": patch_checks,
        "overall_patched_verification": parsed.magic_valid
        and all(block.valid for block in parsed.checksum_blocks)
        and host_hash_ok
        and all(patch_checks.values()),
    }


def dataclass_dict_with(row: Any, extra: dict[str, Any]) -> dict[str, Any]:
    output = asdict(row)
    output.update(extra)
    return output


def patch_gcd(
    input_path: Path,
    output_path: Path,
    dry_run: bool,
    overwrite: bool = False,
) -> dict[str, Any]:
    require_distinct_paths([("input", input_path), ("output", output_path)])
    input_blob = input_path.read_bytes()
    parsed = parse_gcd(input_path, input_blob)
    region, host, host_payload = validate_base(parsed, input_blob)

    patched_blob = bytearray(input_blob)
    spans_written, bytes_written = apply_delta(patched_blob, host)

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
        "detected_region": region,
        "input_size": len(input_blob),
        "output_size": len(patched_blob),
        "input_sha256": sha256_bytes(input_blob),
        "output_sha256": sha256_bytes(bytes(patched_blob)),
        "known_stock_region": True,
        "host_sha256": sha256_bytes(host_payload),
        "delta_spans_applied": spans_written,
        "delta_bytes_applied": bytes_written,
        "features": [
            {
                "name": check.name,
                "fw_offset": hex0(check.fw_offset),
                "description": check.description,
            }
            for check in FEATURES
        ],
        "physical_patch_ranges": [],
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
        atomic_write_bytes(output_path, bytes(patched_blob), overwrite=overwrite)

    return report


def default_output_path(input_path: Path) -> Path:
    return input_path.with_name(input_path.stem + "_patched_v1.2.0" + input_path.suffix)


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
    parser.add_argument("--dry-run", action="store_true", help="Verify and simulate patching without writing the output GCD")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow atomically replacing existing output and report files",
    )
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
    named_paths = [("input", input_path), ("output", output_path)]
    if args.report:
        named_paths.append(("report", args.report))
    try:
        require_distinct_paths(named_paths)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if output_path.exists() and not args.overwrite and not args.dry_run:
        print(f"ERROR: output file exists; use --overwrite or choose another path: {output_path}", file=sys.stderr)
        return 2
    if args.report and args.report.exists() and not args.overwrite:
        print(f"ERROR: report file exists; use --overwrite or choose another path: {args.report}", file=sys.stderr)
        return 2

    try:
        report = patch_gcd(
            input_path=input_path,
            output_path=output_path,
            dry_run=args.dry_run,
            overwrite=args.overwrite,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.report:
        try:
            atomic_write_text(
                args.report,
                json.dumps(report, indent=2) + "\n",
                overwrite=args.overwrite,
            )
        except Exception as exc:
            if args.dry_run:
                print(f"ERROR: report was not written: {exc}", file=sys.stderr)
                return 1
            print(
                "ERROR: patched GCD was written and verified, but the JSON "
                f"report was not written: {exc}",
                file=sys.stderr,
            )
            return 3

    print(f"{TOOL_NAME} {TOOL_VERSION}")
    print(f"Input SHA-256:  {report['input_sha256']}")
    print(f"Output SHA-256: {report['output_sha256']}")
    print(f"Detected region: {report['detected_region']}")
    print(f"Verification: {report['verification']['overall_patched_verification']}")
    if args.dry_run:
        print("Dry run only; no output file written.")
    else:
        print(f"Wrote: {output_path}")
    print(f"Expected patched host SHA-256: {EXPECTED_PATCHED_HOST_SHA256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
