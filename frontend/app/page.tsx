import Header from "@/components/header";
import Workbench from "@/components/workbench";

export default function Home() {
  return (
    <div className="flex min-h-dvh flex-col bg-[#F7F7F8] lg:h-dvh lg:overflow-hidden">
      <Header />
      <Workbench />
    </div>
  );
}
