import { notFound } from "next/navigation";
import { getAllRepos, getRepoToc } from "@/lib/wiki";
import { getLineHue } from "@/lib/stations";
import { Masthead } from "@/components/masthead";
import { LineRail } from "@/components/line-rail";

export const instant = false;

export async function generateStaticParams() {
  const repos = await getAllRepos();
  return repos.map((repo) => ({ repo: repo.repo_name }));
}

interface WikiRepoLayoutProps {
  children: React.ReactNode;
  params: Promise<{ repo: string }>;
}

export default async function WikiRepoLayout({
  children,
  params,
}: WikiRepoLayoutProps) {
  const { repo } = await params;
  const [currentRepo, allRepos] = await Promise.all([
    getRepoToc(repo),
    getAllRepos(),
  ]);

  if (!currentRepo) {
    notFound();
  }

  return (
    <div className="flex min-h-screen flex-col bg-paper">
      <a href="#content" className="skip-link">
        Skip to the reading column
      </a>
      <Masthead />
      <div className="mx-auto flex w-full max-w-[1600px] flex-1 flex-col overflow-x-clip lg:flex-row">
        <LineRail
          currentRepo={currentRepo}
          allRepos={allRepos}
          hue={getLineHue(currentRepo.repo_name)}
          generated={null}
        />
        <div id="content" className="min-w-0 flex-1">
          {children}
        </div>
      </div>
    </div>
  );
}
