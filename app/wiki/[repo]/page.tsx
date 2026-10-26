import { notFound, redirect } from "next/navigation";
import { getAllRepos, getRepoToc } from "@/lib/wiki";

export const instant = false;

export async function generateStaticParams() {
  const repos = await getAllRepos();
  return repos.map((repo) => ({ repo: repo.repo_name }));
}

interface WikiRepoIndexPageProps {
  params: Promise<{ repo: string }>;
}

/** A line's front door is its first station. */
export default async function WikiRepoIndexPage({
  params,
}: WikiRepoIndexPageProps) {
  const { repo } = await params;
  const toc = await getRepoToc(repo);

  if (!toc || toc.pages.length === 0) {
    notFound();
  }

  redirect(`/wiki/${repo}/${toc.pages[0].slug}`);
}
