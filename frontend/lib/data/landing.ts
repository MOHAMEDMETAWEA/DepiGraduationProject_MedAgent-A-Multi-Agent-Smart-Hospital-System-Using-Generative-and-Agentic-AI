import { Shield, Globe, FileText, MessageSquare, Brain, Activity } from "lucide-react";
import { type LucideIcon } from "lucide-react";

export interface Feature {
  icon: LucideIcon;
  title: string;
  desc: string;
}

export interface Step {
  icon: LucideIcon;
  title: string;
  desc: string;
}

export interface TriageLevel {
  level: string;
  headline: string;
  desc: string;
  barColor: string;
  textColor: string;
  bgColor: string;
}

export const FEATURES: Feature[] = [
  {
    icon: Shield,
    title: "Grounded in medical sources",
    desc: "Every answer is checked against established medical guidelines and trusted health databases.",
  },
  {
    icon: Globe,
    title: "Speaks Arabic & English",
    desc: "Switch languages anytime, even in the same message. The interface adapts fully to Arabic.",
  },
  {
    icon: FileText,
    title: "Ready for your doctor",
    desc: "Share a structured summary with your physician before you arrive, so they have context.",
  },
];

export const STEPS: Step[] = [
  {
    icon: MessageSquare,
    title: "Describe your symptoms",
    desc: "Type in Arabic, English, or both.",
  },
  {
    icon: Brain,
    title: "Answer a few questions",
    desc: "The assistant asks clear, simple follow-ups.",
  },
  {
    icon: Activity,
    title: "Get your next step",
    desc: "Receive guidance on where to go and how soon.",
  },
];

export const TRIAGE: TriageLevel[] = [
  {
    level: "Emergency",
    headline: "Call emergency services now",
    desc: "Symptoms include chest pain, difficulty breathing, or severe bleeding.",
    barColor: "bg-rose-500",
    textColor: "text-rose-700",
    bgColor: "bg-rose-50",
  },
  {
    level: "Urgent",
    headline: "See a clinician today",
    desc: "Symptoms include high fever, severe pain, or worsening conditions.",
    barColor: "bg-amber-500",
    textColor: "text-amber-700",
    bgColor: "bg-amber-50",
  },
  {
    level: "Routine",
    headline: "Monitor at home",
    desc: "Symptoms include mild cold, headache, or minor soreness.",
    barColor: "bg-emerald-500",
    textColor: "text-emerald-700",
    bgColor: "bg-emerald-50",
  },
];

export const SAFETY_GATES = [
  "Red-flag detection",
  "Source verification",
  "Uncertainty flagging",
  "Audit logging",
  "Human handoff",
];

export const TRUST_PILLS = [
  "Free, no credit card",
  "Arabic & English",
  "Encrypted & private",
];
