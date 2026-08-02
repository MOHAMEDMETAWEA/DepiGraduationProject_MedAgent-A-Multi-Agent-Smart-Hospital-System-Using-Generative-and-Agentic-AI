const SECTION_HEADERS = [
  "Chief Complaint",
  "الشكوى الرئيسية",
  "الشكوى",
];

const STOP_HEADERS = [
  "Patient History",
  "History",
  "التاريخ المرضي",
  "التاريخ",
  "Triage",
  "الفرز",
  "Vitals",
  "Assessment",
  "Plan",
];

function stripInlineFormatting(s: string): string {
  return s
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/\*(.+?)\*/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\s+/g, " ")
    .trim();
}

export function extractChiefComplaint(md: string): string {
  if (!md) return "";

  for (const header of SECTION_HEADERS) {
    const headerPattern = `##+\\s*${header.replace(/[.*+?^${}()|[\\]\\\\]/g, "\\$&")}`;
    const stopPattern = STOP_HEADERS.map((h) =>
      h.replace(/[.*+?^${}()|[\\]\\\\]/g, "\\$&"),
    ).join("|");
    const re = new RegExp(
      `${headerPattern}\\s*([\\s\\S]*?)(?:##+\\s*(?:${stopPattern})|$)`,
      "i",
    );
    const m = md.match(re);
    if (m && m[1]) {
      const cleaned = stripInlineFormatting(m[1]);
      if (cleaned.length > 0) return cleaned;
    }
  }

  const fallback = md
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0 && !line.startsWith("#") && !/^\*\*Date:/i.test(line))
    .map(stripInlineFormatting)
    .find((line) => line.length > 0);

  return fallback ?? "";
}
