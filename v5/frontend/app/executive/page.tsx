import { ExecutiveDashboardClient } from "@/components/executive/executive-dashboard-client";

export const metadata = {
  title: "Executive Intelligence | Risk Console",
  description: "高层风控 intelligence overview — cross-investigation risk patterns",
};

export default function ExecutivePage() {
  return <ExecutiveDashboardClient />;
}
