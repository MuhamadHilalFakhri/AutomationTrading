"use client"

import * as React from "react"
import { DayPicker } from "react-day-picker"
import { ChevronLeft, ChevronRight } from "lucide-react"

import { cn } from "@/lib/utils"

function Calendar({
  className,
  classNames,
  showOutsideDays = true,
  ...props
}: React.ComponentProps<typeof DayPicker>) {
  return (
    <DayPicker
      showOutsideDays={showOutsideDays}
      className={cn("p-3", className)}
      classNames={{
        months: "flex flex-col sm:flex-row gap-4",
        month: "space-y-4",
        month_caption: "relative flex h-9 items-center justify-center",
        caption_label: "text-sm font-medium text-slate-100",
        nav: "absolute inset-x-0 top-0 flex h-9 items-center justify-between",
        button_previous: "inline-flex h-9 w-9 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-white/[0.08] hover:text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400/70 disabled:pointer-events-none disabled:opacity-30",
        button_next: "inline-flex h-9 w-9 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-white/[0.08] hover:text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400/70 disabled:pointer-events-none disabled:opacity-30",
        month_grid: "w-full border-collapse",
        weekdays: "flex",
        weekday: "flex-1 rounded-md text-center text-xs font-medium tracking-normal text-slate-500",
        week: "mt-1 flex w-full",
        day: "relative h-9 w-9 flex-1 p-0 text-center text-sm",
        day_button: "mx-auto inline-flex h-9 w-9 items-center justify-center rounded-lg p-0 font-mono text-[13px] font-normal text-slate-300 transition-colors hover:bg-white/[0.08] hover:text-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400/70",
        selected: "[&>button]:bg-blue-500 [&>button]:text-white [&>button]:hover:bg-blue-500",
        today: "[&>button]:bg-white/[0.08] [&>button]:font-semibold [&>button]:text-blue-200",
        outside: "text-slate-600 opacity-60",
        disabled: "text-slate-700 opacity-40",
        hidden: "invisible",
        ...classNames,
      }}
      components={{
        Chevron: ({ orientation, ...iconProps }) =>
          orientation === "left" ? <ChevronLeft className="h-4 w-4" {...iconProps} /> : <ChevronRight className="h-4 w-4" {...iconProps} />,
      }}
      {...props}
    />
  )
}

export { Calendar }
