"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { api } from "@/lib/api";
import { ListingCondition } from "@/lib/types";

interface ListingFormProps {
  initialData?: {
    title: string;
    description: string;
    price: number;
    condition?: ListingCondition;
    location?: string;
    min_price?: number;
    seller_notes?: string;
  };
  listingId?: number;
  onSuccess?: () => void;
  onCancel?: () => void;
}

const CONDITIONS: { value: ListingCondition; label: string }[] = [
  { value: "new", label: "New" },
  { value: "like_new", label: "Like New" },
  { value: "good", label: "Good" },
  { value: "fair", label: "Fair" },
];

export function ListingForm({ initialData, listingId, onSuccess, onCancel }: ListingFormProps) {
  const router = useRouter();
  const [title, setTitle] = useState(initialData?.title || "");
  const [description, setDescription] = useState(initialData?.description || "");
  const [price, setPrice] = useState(initialData?.price?.toString() || "");
  const [minPrice, setMinPrice] = useState(initialData?.min_price?.toString() || "");
  const [condition, setCondition] = useState<ListingCondition>(initialData?.condition || "good");
  const [location, setLocation] = useState(initialData?.location || "");
  const [sellerNotes, setSellerNotes] = useState(initialData?.seller_notes || "");
  const [images, setImages] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setImages((prev) => [...prev, ...acceptedFiles]);
    const newPreviews = acceptedFiles.map((file) => URL.createObjectURL(file));
    setPreviews((prev) => [...prev, ...newPreviews]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "image/*": [".jpeg", ".jpg", ".png", ".gif", ".webp"] },
    multiple: true,
  });

  const removeImage = (index: number) => {
    URL.revokeObjectURL(previews[index]);
    setImages((prev) => prev.filter((_, i) => i !== index));
    setPreviews((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const priceValue = parseFloat(price);
      if (isNaN(priceValue) || priceValue <= 0) {
        throw new Error("Please enter a valid price");
      }

      const minPriceValue = minPrice ? parseFloat(minPrice) : undefined;

      if (listingId) {
        await api.listings.update(listingId, {
          title,
          description,
          price: priceValue,
          condition,
          location: location || undefined,
          min_price: minPriceValue,
          seller_notes: sellerNotes || undefined,
          images,
        });
      } else {
        await api.listings.create({
          title,
          description,
          price: priceValue,
          condition,
          location: location || undefined,
          min_price: minPriceValue,
          seller_notes: sellerNotes || undefined,
          images,
        });
      }

      if (onSuccess) {
        onSuccess();
      } else {
        router.push("/home");
      }
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <h2 className="font-bold text-lg">
          {listingId ? "Edit Listing" : "Create New Listing"}
        </h2>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="p-4 bg-primary/10 border-2 border-ink text-primary font-bold text-sm">
              {error}
            </div>
          )}

          <Input
            label="Title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="What are you selling?"
            required
          />

          <Textarea
            label="Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe your item"
            rows={4}
            required
          />

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Price"
              type="number"
              step="0.01"
              min="0.01"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder="0.00"
              required
            />
            <Input
              label="Min Price"
              type="number"
              step="0.01"
              min="0.01"
              value={minPrice}
              onChange={(e) => setMinPrice(e.target.value)}
              placeholder="Lowest you'll accept"
            />
          </div>

          {/* Condition Button Group */}
          <div className="space-y-1.5">
            <label className="block text-sm font-bold text-ink">Condition</label>
            <div className="flex gap-0">
              {CONDITIONS.map((c) => (
                <button
                  key={c.value}
                  type="button"
                  onClick={() => setCondition(c.value)}
                  className={`flex-1 px-3 py-2.5 text-sm font-bold border-2 border-ink transition-all -ml-0.5 first:ml-0 ${
                    condition === c.value
                      ? "bg-secondary text-white neo-shadow-sm z-10 relative"
                      : "bg-surface text-ink hover:bg-cream"
                  }`}
                >
                  {c.label}
                </button>
              ))}
            </div>
          </div>

          <Input
            label="Location"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="e.g. Seattle, WA or 98101"
            required
          />

          <Textarea
            label="Notes for AI Negotiator"
            value={sellerNotes}
            onChange={(e) => setSellerNotes(e.target.value)}
            placeholder="Private notes the AI will use when negotiating (e.g. 'firm on price', 'willing to include accessories')"
            rows={3}
          />

          {/* Dropzone */}
          <div className="space-y-1.5">
            <label className="block text-sm font-bold text-ink">Images</label>
            <div
              {...getRootProps()}
              className={`border-2 border-dashed p-8 text-center cursor-pointer transition-all ${
                isDragActive
                  ? "border-secondary bg-secondary/10"
                  : "border-ink/30 hover:border-ink/60"
              }`}
            >
              <input {...getInputProps()} />
              <p className="text-ink/50 font-medium">
                {isDragActive
                  ? "Drop images here..."
                  : "Drag & drop images, or click to select"}
              </p>
            </div>

            {previews.length > 0 && (
              <div className="grid grid-cols-4 gap-3 mt-3">
                {previews.map((preview, index) => (
                  <div key={index} className="relative aspect-square border-2 border-ink overflow-hidden">
                    <img
                      src={preview}
                      alt={`Preview ${index + 1}`}
                      className="w-full h-full object-cover"
                    />
                    <button
                      type="button"
                      onClick={() => removeImage(index)}
                      className="absolute top-1 right-1 w-6 h-6 bg-primary text-white border border-ink flex items-center justify-center text-xs font-bold hover:bg-primary/80"
                    >
                      x
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="flex gap-4">
            <Button type="submit" disabled={loading}>
              {loading ? "Saving..." : listingId ? "Update Listing" : "Create Listing"}
            </Button>
            <Button type="button" variant="ghost" onClick={() => (onCancel ? onCancel() : router.back())}>
              Cancel
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
