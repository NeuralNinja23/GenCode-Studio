import React from 'react';
import { LoaderCircleIcon } from './Icons';

export const Spinner: React.FC = () => {
  return (
    <div className="flex flex-col items-center gap-2 text-zinc-400">
      <LoaderCircleIcon className="h-10 w-10 animate-spin text-purple-500" />
      <span className="text-sm font-medium">Initializing Preview...</span>
      <span className="sr-only">Loading...</span>
    </div>
  );
};
