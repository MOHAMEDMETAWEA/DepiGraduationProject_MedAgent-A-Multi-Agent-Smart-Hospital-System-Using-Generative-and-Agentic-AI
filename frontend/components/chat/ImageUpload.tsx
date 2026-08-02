"use client";

import { motion } from "framer-motion";
import { ImagePlus, Upload, X } from "lucide-react";
import Image from "next/image";
import { useEffect, useRef, useState, type DragEvent } from "react";
import { springSmooth } from "@/lib/motion";

interface ImageUploadProps {
  onImageSelect: (file: File | null) => void;
  disabled?: boolean;
  /** Externally-controlled clear signal — incrementing this resets the preview. */
  resetSignal?: number;
}

const MAX_SIZE_MB = 10;
const ACCEPTED = "image/jpeg,image/png,image/webp,image/heic";

export function ImageUpload({ onImageSelect, disabled, resetSignal }: ImageUploadProps) {
  const [dragOver, setDragOver] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Parent-driven reset (e.g., after sending a message). The signal is a
  // counter from outside this component, so we must apply it via an effect.
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (resetSignal === undefined) return;
    setPreview(null);
    setError(null);
    if (inputRef.current) inputRef.current.value = "";
  }, [resetSignal]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const validate = (file: File): string | null => {
    if (!ACCEPTED.split(",").includes(file.type)) {
      return "Only JPEG, PNG, WebP, and HEIC images are supported";
    }
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      return `Image must be under ${MAX_SIZE_MB}MB`;
    }
    return null;
  };

  const handleFile = (file: File) => {
    setError(null);
    const err = validate(file);
    if (err) { setError(err); return; }

    const url = URL.createObjectURL(file);
    setPreview(url);
    onImageSelect(file);
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const handleRemove = () => {
    setPreview(null);
    setError(null);
    if (inputRef.current) inputRef.current.value = "";
    onImageSelect(null);
  };

  if (preview) {
    return (
      <div className="relative inline-block">
        <Image
          src={preview}
          alt="Preview"
          width={80}
          height={80}
          className="h-20 w-20 rounded-xl object-cover border border-line"
          unoptimized
        />
        <button
          type="button"
          onClick={handleRemove}
          className="absolute -top-1.5 -right-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-ink-2 text-white text-xs"
        >
          <X className="h-3 w-3" />
        </button>
      </div>
    );
  }

  return (
    <div>
      <motion.div
        whileTap={{ scale: 0.97 }}
        transition={springSmooth}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`flex cursor-pointer items-center gap-2 rounded-xl border-2 border-dashed px-3 py-2 text-xs font-medium transition-colors ${
          dragOver
            ? "border-primary bg-primary/10 text-primary"
            : "border-border text-muted-foreground hover:border-primary/40 hover:text-primary"
        } ${disabled ? "pointer-events-none opacity-40" : ""}`}
      >
        {dragOver ? <Upload className="h-3.5 w-3.5" /> : <ImagePlus className="h-3.5 w-3.5" />}
        <span>{dragOver ? "Drop image here" : "Attach image"}</span>
      </motion.div>

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(file);
        }}
      />

      {error && <p className="mt-1 text-[11px] text-emergency">{error}</p>}
    </div>
  );
}
