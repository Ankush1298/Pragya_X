import { useEffect, useState, type ReactNode } from "react";
import { api, setUnauthorizedHandler, tokenStore } from "./api/client";
import type { User } from "./types/api";
import type { RoutePath } from "./types/routes";
import { AppLayout } from "./components/layout";
import { LoadingState } from "./components/ui";
import { navigate, useAppRouter } from "./routes/router";
import AuthPage from "./pages/AuthPage";
import DashboardPage from "./pages/DashboardPage";
import ChatPage from "./pages/ChatPage";
import SubjectsPage from "./pages/SubjectsPage";
import AssessmentPage from "./pages/AssessmentPage";
import ResultPage from "./pages/ResultPage";
import HistoryPage from "./pages/HistoryPage";
import ChallengePage from "./pages/ChallengePage";

import LearnPage from "./pages/LearnPage";
import ModulePage from "./pages/ModulePage";
import ChallengeLibraryPage from "./pages/ChallengeLibraryPage";
import SettingsPage from "./pages/SettingsPage";
import { notifications } from "./api/learn";
import TeamsPage from "./pages/TeamsPage";
import ProjectsPage from "./pages/ProjectsPage";
import BattlesPage from "./pages/BattlesPage";
import { ProfilePage, VerifyPage, ReferralsPage, RewardsPage, NotificationsPage } from "./pages/GrowthPages";
import { CompetitionsPage, LeaderboardsPage, AdminPage } from "./pages/CompetitionPages";

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(!!tokenStore.get());
  const [unread,setUnread] = useState(0);
  const refreshUnread = () => notifications.unread().then(d=>setUnread(d.unread)).catch(()=>{});
  const [aiIsMock, setAiIsMock] = useState(true);
  const { route, param, param2 } = useAppRouter();

  useEffect(() => { if(user) refreshUnread(); },[user,route]);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      tokenStore.clear();
      setUser(null);
    });

    api
      .health()
      .then((h) => setAiIsMock(h.ai_is_mock))
      .catch(() => {});

    if (tokenStore.get()) {
      api
        .me()
        .then(setUser)
        .catch(() => tokenStore.clear())
        .finally(() => setChecking(false));
    }
  }, []);

  const onAuth = (u: User, token: string, isNew: boolean) => {
    tokenStore.set(token);
    setUser(u);
    // Guided flow: new learners start in chat, returning learners land on dashboard
    navigate(isNew ? "learn" : "dashboard");
  };

  const onLogout = async () => {
    await api.logout().catch(() => {});
    tokenStore.clear();
    setUser(null);
  };

  if (checking) {
    return <LoadingState label="Restoring your session…" fullPage />;
  }

  if (route === "verify") return <VerifyPage id={param} />;

  if (!user) {
    return <AuthPage onAuth={onAuth} />;
  }

  const renderCurrentPage = (currentRoute: RoutePath): ReactNode => {
    switch (currentRoute) {
      case "learn": return <LearnPage key={param ?? "hub"} chatId={param} />;
      case "module": return <ModulePage key={`${param}/${param2}`} chatId={param} moduleId={param2} />;
      case "settings": return <SettingsPage onSaved={()=>api.me().then(setUser)} />;
      case "teams": return <TeamsPage id={param} />;
      case "projects": return <ProjectsPage />;
      case "battles": return <BattlesPage key={param ?? "hub"} battleId={param} />;
      case "competitions": return <CompetitionsPage id={param} />;
      case "leaderboards": return <LeaderboardsPage />;
      case "profile": return <ProfilePage />;
      case "rewards": return <RewardsPage />;
      case "referrals": return <ReferralsPage />;
      case "notifications": return <NotificationsPage onChange={refreshUnread} />;
      case "admin": return <AdminPage />;
      case "dashboard":
        return <DashboardPage />;
      case "chat":
        return <ChatPage />;
      case "subjects":
        return <SubjectsPage />;
      case "assessment":
        return <AssessmentPage />;
      case "results":
        return <HistoryPage />;
      case "result":
        return <ResultPage id={param ?? ""} />;
      case "library": return <ChallengeLibraryPage />;
      case "challenge":
        return <ChallengePage />;
      default:
        return <DashboardPage />;
    }
  };

  return (
    <AppLayout
      user={user}
      active={route}
      aiIsMock={aiIsMock}
      unread={unread}
      onLogout={onLogout}
    >
      {renderCurrentPage(route)}
    </AppLayout>
  );
}
