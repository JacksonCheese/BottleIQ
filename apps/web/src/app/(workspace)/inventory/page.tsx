"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { useWorkspace } from "@/components/workspace";
import { InventoryTable } from "@/components/inventory-table";
import { PageTitle, Loading, ErrorState } from "@/components/ui";
import { useResource } from "@/lib/use-resource";
import type { Metric } from "@/lib/types";
function Inventory() {
  const { store } = useWorkspace();
  const params = useSearchParams();
  const { data, error, reload } = useResource<Metric[]>(
    `/inventory?store_id=${store.id}`,
  );
  return (
    <>
      <PageTitle
        eyebrow="EVERY BOTTLE HAS A STORY"
        title="Your inventory."
        action={
          <Link className="button secondary" href="/imports">
            Update inventory
          </Link>
        }
      >
        Know what’s moving, what’s running low, and what’s holding cash.
      </PageTitle>
      {error ? (
        <ErrorState message={error} retry={reload} />
      ) : data ? (
        <InventoryTable
          products={data}
          initialStatus={params.get("status") || ""}
        />
      ) : (
        <Loading />
      )}
    </>
  );
}
export default function Page() {
  return (
    <Suspense fallback={<Loading />}>
      <Inventory />
    </Suspense>
  );
}
