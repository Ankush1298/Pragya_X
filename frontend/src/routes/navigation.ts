import {
  Bell,
  FolderKanban,
  Gift,
  History,
  LayoutDashboard,
  Medal,
  MessagesSquare,
  Shield,
  Swords,
  Trophy,
  UserPlus,
  UserRound,
  Zap,
} from "lucide-react";
import type { NavItem, RoutePath } from "../types/routes";

/** Every routable path (hash router). Legacy single-chat pages stay reachable by URL; nav shows the new flow. */
export const ROUTE_PATHS: RoutePath[] = [
  "dashboard", "chat", "subjects", "assessment", "results", "result", "library", "challenge",
  "learn", "module", "teams", "projects", "battles", "competitions", "leaderboards", "profile",
  "rewards", "referrals", "settings", "notifications", "admin", "verify",
];

export const NAVIGATION_ITEMS: readonly NavItem[] = [
  { path: "dashboard", label: "Dashboard", icon: LayoutDashboard, category: "learn", description: "Your learning overview" },
  { path: "learn", label: "My Learning Chats", icon: MessagesSquare, category: "learn", description: "One chat per subject: mentor, diagnostic, roadmap and practice" },
  { path: "teams", label: "Team Projects", icon: UserPlus, category: "learn", description: "Collaborate in a team of four or five" },
  { path: "projects", label: "Projects", icon: FolderKanban, category: "learn", description: "Build real things at four levels" },
  { path: "library", label: "Challenge Library", icon: Zap, category: "compete" },
  { path: "challenge", label: "Daily Challenge", icon: Zap, category: "compete", description: "One question a day to build a streak" },
  { path: "battles", label: "1v1 Battles", icon: Swords, category: "compete", description: "Challenge another student" },
  { path: "competitions", label: "Competitions", icon: Trophy, category: "compete", description: "College, company and student-hosted challenges" },
  { path: "leaderboards", label: "Leaderboards", icon: Medal, category: "compete", description: "See how you rank" },
  { path: "profile", label: "Skill Profile", icon: UserRound, category: "growth", description: "Skills, achievements and certificates" },
  { path: "results", label: "My Results", icon: History, category: "growth", description: "Assessment history" },
  { path: "rewards", label: "Rewards", icon: Gift, category: "growth", description: "XP ledger and demo rewards" },
  { path: "referrals", label: "Referrals", icon: UserPlus, category: "growth", description: "Invite friends" },
  { path: "settings", label: "Account Settings", icon: UserRound, category: "account" },
  { path: "notifications", label: "Notifications", icon: Bell, category: "account", description: "Alerts and preferences" },
  { path: "admin", label: "Admin", icon: Shield, category: "admin", description: "Platform administration" },
] as const;

export const NAV_SECTIONS: { key: NavItem["category"]; title: string }[] = [
  { key: "learn", title: "Learn" },
  { key: "compete", title: "Compete" },
  { key: "growth", title: "My Growth" },
  { key: "account", title: "Account" },
  { key: "admin", title: "Administration" },
];

export const ROUTE_TITLES: Record<RoutePath, string> = {
  dashboard: "Dashboard",
  chat: "Learning Chat",
  subjects: "Choose Subject",
  assessment: "Assessment",
  library: "Challenge Library",
  challenge: "Daily Challenge",
  results: "My Results",
  result: "Assessment Review",
  learn: "My Learning Chats",
  module: "Lesson",
  teams: "Team Projects",
  projects: "Projects",
  battles: "1v1 Battles",
  competitions: "Competitions",
  leaderboards: "Leaderboards",
  profile: "Skill Profile",
  rewards: "Rewards",
  referrals: "Referrals",
  settings: "Account Settings",
  notifications: "Notifications",
  admin: "Admin",
  verify: "Verify Achievement",
};
