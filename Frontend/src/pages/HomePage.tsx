import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getApiUrl } from '../config/env';
import { GithubIcon, MicIcon, GlobeIcon, SendIcon, RefreshCwIcon, LoaderCircleIcon, SparklesIcon, ZapIcon, RocketIcon, LayersIcon, ClockIcon } from '../components/Icons';
import { Project } from '../types';
import Providers from '../components/Providers';
import MatrixBackground from '../components/MatrixBackground';

const PROMPT_EXAMPLES = [
  { text: "A task manager with auth and analytics", icon: "📋" },
  { text: "A blog platform with markdown editor", icon: "✍️" },
  { text: "E‑commerce storefront with cart", icon: "🛒" },
  { text: "Surprise Me", icon: "✨" },
];



const HomePage: React.FC = () => {
  const [prompt, setPrompt] = useState('');
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchProjects = async () => {
      try {
        const url = getApiUrl('/api/projects');
        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to fetch projects');
        const data: Project[] = await response.json();
        setProjects(data);
      } catch (error) {
        console.error("Error fetching projects:", error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchProjects();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (prompt.trim() && !isSubmitting) {
      setIsSubmitting(true);
      try {
        const postUrl = getApiUrl('/api/projects');
        const response = await fetch(postUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt }),
        });
        if (!response.ok) throw new Error(`Failed to create project: ${response.statusText}`);
        const newProject: Project = await response.json();
        navigate(`/workspace/${newProject.id}`, { state: { prompt } });
      } catch (error) {
        console.error("Error creating project:", error);
      } finally {
        setIsSubmitting(false);
      }
    }
  };

  const handleProjectClick = (project: Project) => {
    navigate(`/workspace/${project.id}`, { state: { prompt: project.description } });
  };

  return (
    <div className="min-h-screen relative">
      {/* Hero Section */}
      <section className="relative overflow-hidden px-4 pt-20 pb-32 sm:px-6 lg:px-8">
        {/* Matrix Background - only in hero section */}
        <div className="absolute inset-0 z-0">
          <MatrixBackground opacity={0.20} />
        </div>

        {/* Animated gradient orbs */}
        <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-purple-500/20 rounded-full blur-[120px] animate-pulse" />
        <div className="absolute top-20 right-1/4 w-[400px] h-[400px] bg-cyan-500/20 rounded-full blur-[100px] animate-pulse" style={{ animationDelay: '1s' }} />
        <div className="absolute bottom-0 left-1/2 w-[600px] h-[300px] bg-indigo-500/5 rounded-full blur-[120px]" />

        <div className="relative container mx-auto max-w-6xl">
          <div className="text-center">
            {/* Badge */}
            <div className="inline-flex items-center gap-2 rounded-full border border-purple-500/30 bg-purple-500/10 px-4 py-1.5 text-sm text-purple-300 backdrop-blur-sm mb-8 animate-fade-in">
              <SparklesIcon className="h-4 w-4" />
              <span>AI-Powered App Generation</span>
            </div>

            {/* Main Headline */}
            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight leading-tight">
              <span className="block text-white">Build apps with an</span>
              <span className="block mt-2 bg-gradient-to-r from-purple-400 via-violet-400 to-indigo-400 bg-clip-text text-transparent">
                AI expert in your browser
              </span>
            </h1>

            {/* Subtitle */}
            <p className="mt-8 max-w-2xl mx-auto text-lg sm:text-xl text-zinc-400 leading-relaxed">
              Describe what you want and GenCode will plan, implement, test, and preview a working application you can iterate on.
            </p>

            {/* Prompt Input */}
            <form onSubmit={handleSubmit} className="mt-12 w-full max-w-3xl mx-auto z-10 relative">
              <div className="group relative rounded-2xl border border-white/10 bg-zinc-900/80 shadow-2xl shadow-purple-900/20 backdrop-blur-xl transition-all duration-500 focus-within:border-purple-500/50 focus-within:shadow-purple-500/20 hover:border-white/20">
                {/* Glow effect */}
                <div className="absolute -inset-px rounded-2xl bg-gradient-to-r from-purple-500/10 via-transparent to-indigo-500/10 opacity-0 blur transition-opacity duration-500 group-focus-within:opacity-30" />

                <div className="relative">
                  <textarea
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="Describe the app you want — e.g. 'A task manager with user auth and analytics'"
                    className="w-full resize-none bg-transparent p-6 pb-4 text-base sm:text-lg text-zinc-100 placeholder-zinc-500 focus:outline-none disabled:opacity-70"
                    rows={3}
                    disabled={isSubmitting}
                  />

                  <div className="flex items-center justify-between border-t border-white/5 px-4 py-3">
                    <div className="flex items-center gap-1">
                      <button type="button" className="rounded-lg p-2.5 text-zinc-500 transition-all hover:bg-white/5 hover:text-zinc-300">
                        <MicIcon className="h-5 w-5" />
                      </button>
                      <button type="button" className="rounded-lg p-2.5 text-zinc-500 transition-all hover:bg-white/5 hover:text-zinc-300">
                        <GithubIcon className="h-5 w-5" />
                      </button>
                      <div className="h-6 w-px bg-white/10 mx-1" />
                      <Providers />
                    </div>

                    <div className="flex items-center gap-3">
                      <button
                        type="button"
                        className="flex items-center gap-2 rounded-lg border border-white/10 px-4 py-2 text-sm text-zinc-400 transition-all hover:border-white/20 hover:bg-white/5 hover:text-zinc-300"
                      >
                        <GlobeIcon className="h-4 w-4" />
                        Public
                      </button>

                      <button
                        type="submit"
                        className="group/btn relative flex items-center gap-2 rounded-xl px-6 py-2.5 text-sm font-semibold text-white overflow-hidden transition-all duration-300 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                        disabled={!prompt.trim() || isSubmitting}
                      >
                        {/* Button gradient background */}
                        <div className="absolute inset-0 bg-gradient-to-r from-purple-600 via-violet-600 to-indigo-600" />
                        <div className="absolute inset-0 bg-gradient-to-r from-purple-500 via-violet-500 to-indigo-500 opacity-0 transition-opacity group-hover/btn:opacity-100" />

                        {/* Shimmer */}
                        <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/25 to-transparent group-hover/btn:translate-x-full transition-transform duration-700" />

                        {isSubmitting ? (
                          <LoaderCircleIcon className="relative h-5 w-5 animate-spin" />
                        ) : (
                          <>
                            <span className="relative">Generate</span>
                            <SendIcon className="relative h-4 w-4" />
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </form>

            {/* Quick prompts */}
            <div className="mt-8 flex flex-wrap items-center justify-center gap-2">
              {PROMPT_EXAMPLES.map((example) => (
                <button
                  key={example.text}
                  onClick={() => setPrompt(`Build an app: ${example.text}`)}
                  className="group flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-zinc-400 backdrop-blur-sm transition-all duration-300 hover:border-purple-500/30 hover:bg-purple-500/10 hover:text-zinc-200"
                >
                  <span>{example.icon}</span>
                  <span>{example.text}</span>
                </button>
              ))}
              <button className="p-2.5 text-zinc-500 transition-all hover:text-zinc-300 hover:rotate-180 duration-500">
                <RefreshCwIcon className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </section>


      {/* Recent Projects Section */}
      <section className="px-4 py-12 sm:px-6 lg:px-8">
        <div className="container mx-auto max-w-6xl">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-2xl font-bold text-white">Recent Projects</h2>
              <p className="mt-1 text-sm text-zinc-500">Pick up where you left off</p>
            </div>
            <button className="flex items-center gap-2 rounded-lg border border-white/10 px-4 py-2 text-sm text-zinc-400 transition-all hover:border-white/20 hover:bg-white/5 hover:text-white">
              <RefreshCwIcon className="h-4 w-4" />
              Refresh
            </button>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-20">
              <LoaderCircleIcon className="h-8 w-8 animate-spin text-purple-500" />
            </div>
          ) : projects.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <div className="rounded-2xl bg-zinc-900/50 border border-white/5 p-12 backdrop-blur-sm">
                <SparklesIcon className="mx-auto h-12 w-12 text-zinc-600" />
                <h3 className="mt-4 text-lg font-medium text-zinc-300">No projects yet</h3>
                <p className="mt-2 text-sm text-zinc-500">Start by describing your first app above!</p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {projects.map((project) => (
                <div
                  key={project.id}
                  onClick={() => handleProjectClick(project)}
                  className="group relative cursor-pointer overflow-hidden rounded-2xl border border-white/5 bg-zinc-900/50 backdrop-blur-sm transition-all duration-500 hover:border-purple-500/30 hover:shadow-2xl hover:shadow-purple-500/10 hover:-translate-y-1"
                >
                  {/* Project Image */}
                  <div className="relative aspect-video overflow-hidden">
                    <img
                      src={project.imageUrl}
                      alt={project.name}
                      className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-110"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-zinc-900 via-transparent to-transparent" />

                    {/* Hover overlay */}
                    <div className="absolute inset-0 flex items-center justify-center bg-purple-500/20 opacity-0 backdrop-blur-sm transition-opacity duration-300 group-hover:opacity-100">
                      <span className="rounded-full bg-white/10 px-4 py-2 text-sm font-medium text-white backdrop-blur-sm">
                        Open Project
                      </span>
                    </div>
                  </div>

                  {/* Project Info */}
                  <div className="p-5">
                    <h3 className="text-base font-semibold text-white group-hover:text-purple-300 transition-colors">{project.name}</h3>
                    <p className="mt-1.5 text-sm text-zinc-500 line-clamp-2">{project.description}</p>

                    <div className="mt-4 flex items-center gap-2 text-xs text-zinc-600">
                      <ClockIcon className="h-3.5 w-3.5" />
                      <span>Modified {project.lastModified}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
};

export default HomePage;