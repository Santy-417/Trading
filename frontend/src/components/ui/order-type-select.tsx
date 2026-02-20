"use client";

import * as React from "react";
import {
  CheckIcon,
  ChevronsUpDownIcon,
  TrendingUpIcon,
  TrendingDownIcon,
  ZapIcon,
  ArrowUpIcon,
  ArrowDownIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

export type OrderTypeId =
  | "market"
  | "buy_limit"
  | "sell_limit"
  | "buy_stop"
  | "sell_stop";

export interface OrderTypeOption {
  id: OrderTypeId;
  label: string;
  description: string;
  icon: React.ElementType;
  color: string;
}

const ORDER_TYPES: OrderTypeOption[] = [
  {
    id: "market",
    label: "Market Execution",
    description: "Al precio actual de mercado",
    icon: ZapIcon,
    color: "text-blue-400",
  },
  {
    id: "buy_limit",
    label: "Buy Limit",
    description: "Compra por debajo del precio actual",
    icon: TrendingUpIcon,
    color: "text-green-400",
  },
  {
    id: "sell_limit",
    label: "Sell Limit",
    description: "Vende por encima del precio actual",
    icon: TrendingDownIcon,
    color: "text-red-400",
  },
  {
    id: "buy_stop",
    label: "Buy Stop",
    description: "Compra cuando el precio sube a un nivel",
    icon: ArrowUpIcon,
    color: "text-green-400",
  },
  {
    id: "sell_stop",
    label: "Sell Stop",
    description: "Vende cuando el precio baja a un nivel",
    icon: ArrowDownIcon,
    color: "text-red-400",
  },
];

interface OrderTypeSelectProps {
  value: OrderTypeId;
  onValueChange: (value: OrderTypeId) => void;
  className?: string;
}

export function OrderTypeSelect({
  value,
  onValueChange,
  className,
}: OrderTypeSelectProps) {
  const [open, setOpen] = React.useState(false);

  const selected = ORDER_TYPES.find((t) => t.id === value) ?? ORDER_TYPES[0];
  const SelectedIcon = selected.icon;

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
          <div className="flex items-center gap-2 min-w-0">
            <SelectedIcon className={cn("h-4 w-4 shrink-0", selected.color)} />
            <span className="truncate font-medium">{selected.label}</span>
          </div>
          <ChevronsUpDownIcon className="h-4 w-4 shrink-0 opacity-50" />
        </button>
      </PopoverTrigger>
      <PopoverContent
        className="p-0 w-[var(--radix-popover-trigger-width)]"
        align="start"
        sideOffset={4}
      >
        <div className="border-b border-border px-3 py-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Order Type
          </p>
        </div>
        <div className="p-1">
          {ORDER_TYPES.map((orderType) => {
            const Icon = orderType.icon;
            const isSelected = orderType.id === value;
            return (
              <button
                key={orderType.id}
                onClick={() => {
                  onValueChange(orderType.id);
                  setOpen(false);
                }}
                className={cn(
                  "flex w-full items-center gap-3 rounded-sm px-2 py-2 text-left text-sm transition-colors",
                  "hover:bg-accent hover:text-accent-foreground focus:outline-none",
                  isSelected && "bg-accent text-accent-foreground"
                )}
              >
                <Icon className={cn("h-4 w-4 shrink-0", orderType.color)} />
                <div className="flex min-w-0 flex-1 flex-col">
                  <span className="font-medium">{orderType.label}</span>
                  <span className="text-xs text-muted-foreground">
                    {orderType.description}
                  </span>
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

export { ORDER_TYPES };
