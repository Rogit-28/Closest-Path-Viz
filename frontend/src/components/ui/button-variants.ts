import { cva } from 'class-variance-authority';

export const buttonVariants = cva(
  'inline-flex items-center justify-center whitespace-nowrap rounded text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-red-600 disabled:pointer-events-none disabled:opacity-40',
  {
    variants: {
      variant: {
        default: 'bg-neutral-100 text-neutral-950 hover:bg-neutral-200',
        primary: 'bg-red-600 text-white hover:bg-red-500',
        secondary: 'border border-neutral-800 bg-transparent text-neutral-300 hover:bg-neutral-900 hover:text-neutral-100',
        ghost: 'text-neutral-400 hover:bg-neutral-900 hover:text-neutral-200',
        destructive: 'bg-red-700 text-white hover:bg-red-600',
      },
      size: {
        default: 'h-9 px-4 py-2',
        sm: 'h-8 px-3 text-xs',
        lg: 'h-10 px-6',
        icon: 'h-9 w-9',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);
