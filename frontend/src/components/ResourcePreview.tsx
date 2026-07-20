import { useTranslation } from "react-i18next";

import type { ResolvedResource } from "../api";

interface ResourcePreviewProps {
  resource: ResolvedResource;
  selectedItems: Set<number>;
  onSelectedItemsChange: (items: Set<number>) => void;
}

function formatDuration(seconds: number | null, unknownLabel: string): string {
  if (!seconds) return unknownLabel;
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remaining = Math.floor(seconds % 60);
  return [hours, minutes, remaining]
    .filter((_, index) => hours > 0 || index > 0)
    .map((value) => String(value).padStart(2, "0"))
    .join(":");
}

export function ResourcePreview({
  resource,
  selectedItems,
  onSelectedItemsChange,
}: ResourcePreviewProps) {
  const { t } = useTranslation();
  const allSelected =
    resource.items.length > 0
    && resource.items.every((item) => selectedItems.has(item.index));

  function toggle(index: number) {
    const next = new Set(selectedItems);
    if (next.has(index)) next.delete(index);
    else next.add(index);
    onSelectedItemsChange(next);
  }

  return (
    <section className="panel resource-preview" aria-labelledby="resource-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">
            {t(`resource.kinds.${resource.kind}`)} · {resource.total_items}
          </p>
          <h2 id="resource-heading">{resource.title}</h2>
          <p className="video-meta">
            {resource.uploader ?? t("video.unknownUploader")}
            {resource.experimental ? ` · ${t("resource.experimental")}` : ""}
          </p>
        </div>
        {resource.thumbnail && (
          <img
            className="resource-thumbnail"
            src={resource.thumbnail}
            alt={t("video.coverAlt", { title: resource.title })}
          />
        )}
      </div>
      {resource.warnings.map((warning) => (
        <div className="warning-banner resource-warning" key={warning}>
          {t(`resource.warnings.${warning}`)}
        </div>
      ))}
      <div className="page-toolbar">
        <h3>{t("resource.selectItems")}</h3>
        <button
          type="button"
          className="text-button"
          onClick={() =>
            onSelectedItemsChange(
              allSelected
                ? new Set()
                : new Set(resource.items.map((item) => item.index)),
            )
          }
        >
          {allSelected ? t("video.clearAll") : t("video.selectAll")}
        </button>
      </div>
      <div className="page-list resource-list">
        {resource.items.map((item) => (
          <label className="page-option" key={`${item.index}-${item.id}`}>
            <input
              type="checkbox"
              checked={selectedItems.has(item.index)}
              onChange={() => toggle(item.index)}
            />
            <span className="page-number">#{String(item.index).padStart(2, "0")}</span>
            <span className="page-title">
              {item.title}
              {item.branch ? ` · ${t("resource.branch")}` : ""}
            </span>
            <span className="page-duration">
              {formatDuration(item.duration, t("video.unknownDuration"))}
            </span>
          </label>
        ))}
      </div>
      {resource.truncated && (
        <p className="resource-limit">{t("resource.previewLimit")}</p>
      )}
    </section>
  );
}
