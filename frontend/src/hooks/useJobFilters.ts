import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import type { FilterOptions } from "../types";

const WORK_TYPES = ["remote", "hybrid", "onsite"];

function split(value: string | null): string[] {
  return (value || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

export function jobFilterParams(sp: URLSearchParams): Record<string, string> {
  const params: Record<string, string> = {};
  const source = sp.get("source");
  if (source) params.source = source;
  const location = sp.get("location");
  if (location) params.location = location;
  const workType = sp.get("work_type");
  if (workType && workType !== "all") params.work_type = workType;
  return params;
}

export function useJobFilters() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [options, setOptions] = useState<FilterOptions>({
    sources: [],
    locations: [],
    work_types: WORK_TYPES,
  });

  const sources = split(searchParams.get("source"));
  const locations = split(searchParams.get("location"));
  const workType = searchParams.get("work_type") || "all";

  useEffect(() => {
    api.jobs
      .filters()
      .then((d) => setOptions({ ...d, work_types: WORK_TYPES }))
      .catch(() => {});
  }, []);

  const set = (key: string, value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    setSearchParams(next);
  };

  const setSources = (values: string[]) => set("source", values.join(","));
  const setLocations = (values: string[]) => set("location", values.join(","));
  const setWorkType = (value: string) => set("work_type", value === "all" ? "" : value);

  const clear = () => {
    const next = new URLSearchParams(searchParams);
    next.delete("source");
    next.delete("location");
    next.delete("work_type");
    setSearchParams(next);
  };

  const hasFilters = sources.length > 0 || locations.length > 0 || workType !== "all";

  return {
    options,
    sources,
    locations,
    workType,
    setSources,
    setLocations,
    setWorkType,
    clear,
    hasFilters,
  };
}
