import * as React from "react"
import { cn } from "@/lib/utils"

const Dialog = ({ open, onOpenChange, children, ...props }) => {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm"
        onClick={() => onOpenChange(false)}
      />
      <div
        className="relative z-50 bg-background rounded-lg shadow-lg max-w-lg w-full mx-4 max-h-[85vh] overflow-y-auto"
        {...props}
      >
        {children}
      </div>
    </div>
  )
}
Dialog.displayName = "Dialog"

const DialogTrigger = ({ children, asChild = false, ...props }) => {
  const Comp = asChild ? "div" : "button"
  return <Comp {...props}>{children}</Comp>
}
DialogTrigger.displayName = "DialogTrigger"

const DialogContent = ({ children, className, ...props }) => {
  return (
    <div className={cn("p-6", className)} {...props}>
      {children}
    </div>
  )
}
DialogContent.displayName = "DialogContent"

const DialogHeader = ({ children, className, ...props }) => {
  return (
    <div className={cn("flex flex-col space-y-1.5 text-center sm:text-left mb-4", className)} {...props}>
      {children}
    </div>
  )
}
DialogHeader.displayName = "DialogHeader"

const DialogTitle = ({ children, className, ...props }) => {
  return (
    <h3 className={cn("text-lg font-semibold leading-none tracking-tight", className)} {...props}>
      {children}
    </h3>
  )
}
DialogTitle.displayName = "DialogTitle"

const DialogDescription = ({ children, className, ...props }) => {
  return (
    <p className={cn("text-sm text-muted-foreground", className)} {...props}>
      {children}
    </p>
  )
}
DialogDescription.displayName = "DialogDescription"

const DialogFooter = ({ children, className, ...props }) => {
  return (
    <div className={cn("flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2 mt-6", className)} {...props}>
      {children}
    </div>
  )
}
DialogFooter.displayName = "DialogFooter"

const DialogClose = ({ children, className, ...props }) => {
  return (
    <button type="button" className={cn("inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2", className)} {...props}>
      {children}
    </button>
  )
}
DialogClose.displayName = "DialogClose"

export {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
}
