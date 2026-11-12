"""Validation Finding, RuleSummary, and Report models with deterministic formatting."""

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any

SEVERITIES: tuple[str, ...] = ("CRITICAL", "HIGH", "MEDIUM", "LOW")
SEVERITY_RANK: dict[str, int] = {sev: i for i, sev in enumerate(SEVERITIES)}


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    entity_type: str
    entity_id: str
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.severity not in SEVERITY_RANK:
            raise ValueError(f"Invalid severity: {self.severity!r}")

    def sort_key(self) -> tuple[int, str, str, str, str]:
        return (
            SEVERITY_RANK[self.severity],
            self.rule_id,
            self.entity_type,
            self.entity_id,
            self.message,
        )


@dataclass(frozen=True)
class RuleSummary:
    rule_id: str
    severity: str
    status: str  # "PASS" or "FAIL"
    finding_count: int
    description: str = ""


@dataclass(frozen=True)
class Report:
    findings: list[Finding]
    rule_summaries: list[RuleSummary]
    scale: str = "starter"
    detector_findings: list[Finding] = field(default_factory=list)
    detector_summaries: list[RuleSummary] = field(default_factory=list)

    @property
    def has_critical_or_high(self) -> bool:
        return any(f.severity in ("CRITICAL", "HIGH") for f in self.findings)

    @property
    def passed(self) -> bool:
        return not self.has_critical_or_high

    def findings_for_rule(self, rule_id: str) -> list[Finding]:
        return [f for f in self.findings if f.rule_id == rule_id]

    def format_cli_lines(self) -> list[str]:
        lines: list[str] = ["DATA QUALITY:"]
        for rs in self.rule_summaries:
            lines.append(
                f"  {rs.rule_id:29s} | {rs.status:4s} | findings={rs.finding_count:5d} | severity={rs.severity}"
            )
        if self.detector_summaries:
            lines.append("BUSINESS-RULE DETECTORS:")
            for ds in self.detector_summaries:
                lines.append(
                    f"  {ds.rule_id:29s} | {ds.status:4s} | findings={ds.finding_count:5d} | severity={ds.severity}"
                )
        return lines

    def to_dict(self) -> dict[str, Any]:
        counts_by_severity = {
            sev: sum(1 for f in self.findings if f.severity == sev)
            for sev in SEVERITIES
        }
        return {
            "scale": self.scale,
            "passed": self.passed,
            "has_critical_or_high": self.has_critical_or_high,
            "total_findings": len(self.findings),
            "counts_by_severity": counts_by_severity,
            "rules": [asdict(rs) for rs in self.rule_summaries],
            "findings": [asdict(f) for f in self.findings],
        }

    def to_anomaly_report_dict(self) -> dict[str, Any]:
        sorted_det = sorted(self.detector_findings, key=lambda f: f.sort_key())
        counts_by_detector = {
            ds.rule_id: ds.finding_count for ds in self.detector_summaries
        }
        return {
            "scale": self.scale,
            "total_detector_findings": len(sorted_det),
            "counts_by_detector": counts_by_detector,
            "detectors": [asdict(ds) for ds in self.detector_summaries],
            "findings": [asdict(f) for f in sorted_det],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False) + "\n"

    def to_anomaly_json(self, indent: int = 2) -> str:
        return (
            json.dumps(self.to_anomaly_report_dict(), indent=indent, sort_keys=False)
            + "\n"
        )

    def to_markdown(self) -> str:
        overall = "PASS" if self.passed else "FAIL"
        lines: list[str] = [
            f"# Validation Summary (scale={self.scale})",
            "",
            f"- **Overall Status**: `{overall}`",
            f"- **Total Findings**: `{len(self.findings)}`",
            f"- **Critical / High Findings**: `{sum(1 for f in self.findings if f.severity in ('CRITICAL', 'HIGH'))}`",
            "",
            "## Rule Results",
            "",
            "| Rule ID | Status | Severity | Findings | Description |",
            "| :--- | :--- | :--- | ---: | :--- |",
        ]
        for rs in self.rule_summaries:
            lines.append(
                f"| `{rs.rule_id}` | **{rs.status}** | `{rs.severity}` | {rs.finding_count} | {rs.description} |"
            )

        if self.findings:
            lines.extend(
                [
                    "",
                    "## Findings (First 50)",
                    "",
                    "| Rule ID | Severity | Entity Type | Entity ID | Message |",
                    "| :--- | :--- | :--- | :--- | :--- |",
                ]
            )
            for f in self.findings[:50]:
                lines.append(
                    f"| `{f.rule_id}` | `{f.severity}` | `{f.entity_type}` | `{f.entity_id}` | {f.message} |"
                )
        else:
            lines.extend(["", "No validation findings detected."])

        if self.detector_summaries:
            lines.extend(
                [
                    "",
                    "## Detected business-rule anomalies",
                    "",
                    "| Detector ID | Status | Severity | Findings | Description |",
                    "| :--- | :--- | :--- | ---: | :--- |",
                ]
            )
            for ds in self.detector_summaries:
                lines.append(
                    f"| `{ds.rule_id}` | **{ds.status}** | `{ds.severity}` | {ds.finding_count} | {ds.description} |"
                )

            sorted_det = sorted(self.detector_findings, key=lambda f: f.sort_key())
            for ds in self.detector_summaries:
                rule_det_findings = [
                    f for f in sorted_det if f.rule_id == ds.rule_id
                ][:5]
                lines.extend(
                    [
                        "",
                        f"### `{ds.rule_id}` (First 5 of {ds.finding_count})",
                        "",
                    ]
                )
                if not rule_det_findings:
                    lines.append("No findings.")
                else:
                    lines.extend(
                        [
                            "| Entity Type | Entity ID | Customer ID | Message |",
                            "| :--- | :--- | :--- | :--- |",
                        ]
                    )
                    for df_item in rule_det_findings:
                        cid_str = str(df_item.evidence.get("customer_id", ""))
                        lines.append(
                            f"| `{df_item.entity_type}` | `{df_item.entity_id}` | `{cid_str}` | {df_item.message} |"
                        )

        return "\n".join(lines) + "\n"

    def write_reports(self, output_dir: Path | str) -> tuple[Path, Path]:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        md_path = out / "validation_summary.md"
        json_path = out / "validation_report.json"
        anom_json_path = out / "anomaly_report.json"
        md_path.write_text(self.to_markdown(), encoding="utf-8")
        json_path.write_text(self.to_json(), encoding="utf-8")
        anom_json_path.write_text(self.to_anomaly_json(), encoding="utf-8")
        return md_path, json_path
