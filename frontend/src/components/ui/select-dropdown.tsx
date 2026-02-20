"use client";

import * as React from "react";
import { CheckIcon, ChevronsUpDownIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

export interface SelectOption {
  id: string;
  label: string;
  description?: string;
}

interface SelectDropdownProps {
  options: SelectOption[];
  value: string;
  onValueChange: (value: string) => void;
  label?: string;
  className?: string;
}

export function SelectDropdown({
  options,
  value,
  onValueChange,
  label,
  className,
}: SelectDropdownProps) {
  const [open, setOpen] = React.useState(false);

  const selected = options.find((o) => o.id === value) ?? options[0];

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          data-state={open ? "open" : "closed"}
          className={cn(
            "flex h-10 w-full items-center justify-between rounded-md border border-border bg-popover px-3 py-2 text-sm",
            "text-popover-foreground hover:bg-accent hover:text-accent-foreground",
            "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background",
            "disabled:cursor-not-allowed disabled:opacity-50 transition-colors",
            className
          )}
        >
          <span className="truncate font-medium">{selected?.label ?? value}</span>
          <ChevronsUpDownIcon className="h-4 w-4 shrink-0 opacity-50" />
        </button>
      </PopoverTrigger>
      <PopoverContent
        className="p-0 w-[var(--radix-popover-trigger-width)]"
        align="start"
        sideOffset={4}
      >
        {label && (
          <div className="border-b border-border px-3 py-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {label}
            </p>
          </div>
        )}
        <div className="p-1">
          {options.map((option) => {
            const isSelected = option.id === value;
            return (
              <button
                key={option.id}
                onClick={() => {
                  onValueChange(option.id);
                  setOpen(false);
                }}
                className={cn(
                  "flex w-full items-center gap-3 rounded-sm px-2 py-2 text-left text-sm transition-colors",
                  "hover:bg-accent hover:text-accent-foreground focus:outline-none",
                  isSelected && "bg-accent text-accent-foreground"
                )}
              >
                <div className="flex min-w-0 flex-1 flex-col">
                  <span className="font-medium">{option.label}</span>
                  {option.description && (
                    <span className="text-xs text-muted-foreground">
                      {option.description}
                    </span>
                  )}
                </div>
                {isSelected && (
                  <CheckIcon className="ml-auto h-4 w-4 shrink-0" />
                )}
              </button>
            );
          })}
        </div>
      </PopoverContent>
    </Popover>
  );
}
