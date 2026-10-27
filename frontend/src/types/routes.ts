import type { ComponentType } from "react";
import type { LucideIcon } from "lucide-react";

export type RoutePath =
  | "dashboard"
  | "chat"
  | "subjects"
  | "assessment"
  | "results"
  | "result"
  | "library"
  | "challenge"
  | "learn"
  | "module"
  | "teams"
  | "projects"
  | "battles"
  | "competitions"
  | "leaderboards"
  | "profile"
  | "rewards"
  | "referrals"
  | "settings"
  | "notifications"
  | "admin"
  | "verify";

export type NavCategory = "learn" | "compete" | "growth" | "account" | "admin";

export interface NavItem {
  readonly path: RoutePath;
  readonly label: string;
  readonly icon: LucideIcon;
  readonly category: NavCategory;
  readonly description?: string;
  readonly requiresAuth?: boolean;
}

export interface RouteConfig {
  readonly path: RoutePath;
  readonly title: string;
  readonly subtitle?: string;
  readonly component?: ComponentType<any>;
}

export interface ParsedRoute {
  readonly path: RoutePath;
  readonly param?: string;
  readonly param2?: string;
  readonly fullPath: string;
}
