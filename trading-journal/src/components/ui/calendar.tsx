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
      className={cn("relative w-fit p-3 text-foreground", className)}
      classNames={{
        months: "flex flex-col sm:flex-row gap-4",
        month: "space-y-4",
        month_caption: "relative flex h-9 items-center justify-center",
        caption_label: "text-sm font-medium text-foreground",
        nav: "pointer-events-none absolute inset-x-3 top-3 z-10 flex h-9 items-center justify-between",
        button_previous: "pointer-events-auto inline-flex h-9 w-9 items-center justify-center rounded-full border border-signal bg-transparent text-signal transition-colors hover:bg-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:pointer-events-none disabled:opacity-30",
        button_next: "pointer-events-auto inline-flex h-9 w-9 items-center justify-center rounded-full border border-signal bg-transparent text-signal transition-colors hover:bg-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:pointer-events-none disabled:opacity-30",
        month_grid: "w-full border-collapse",
        weekdays: "flex",
        weekday: "flex-1 text-center text-xs font-medium tracking-normal text-muted-foreground",
        week: "mt-1 flex w-full",
        day: "relative h-9 w-9 flex-1 p-0 text-center text-sm",
        day_button: "mx-auto inline-flex h-9 w-9 items-center justify-center rounded-full bg-transparent p-0 font-mono text-[13px] font-normal text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:pointer-events-none",
        selected: "[&>button]:bg-primary [&>button]:text-primary-foreground [&>button]:hover:bg-primary [&>button]:hover:text-primary-foreground",
        today: "[&>button]:border [&>button]:border-signal [&>button]:font-semibold",
        outside: "text-muted-foreground opacity-60",
        disabled: "text-muted-foreground opacity-40",
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
