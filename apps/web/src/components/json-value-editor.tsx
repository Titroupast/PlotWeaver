"use client";

import { useMemo } from "react";

export type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };

type PathSegment = string | number;

type Props = {
  value: unknown;
  disabled?: boolean;
  onChange: (next: JsonValue) => void;
};

export function JsonValueEditor({ value, disabled, onChange }: Props) {
  const normalized = useMemo(() => normalizeJsonValue(value), [value]);
  return (
    <div className="json-editor">
      <JsonNode
        path={[]}
        label="root"
        value={normalized}
        disabled={disabled}
        onReplace={(next) => onChange(normalizeJsonValue(next))}
      />
    </div>
  );
}

function JsonNode({
  label,
  value,
  path,
  disabled,
  onReplace
}: {
  label: string;
  value: JsonValue;
  path: PathSegment[];
  disabled?: boolean;
  onReplace: (next: JsonValue) => void;
}) {
  if (Array.isArray(value)) {
    return (
      <div className="json-node">
        {path.length > 0 ? (
          <p className="json-node-label">
            <strong>{label}</strong> <span className="muted">数组（固定长度：{value.length}）</span>
          </p>
        ) : null}
        <div className="json-node-children">
          {value.map((item, index) => (
            <JsonNode
              key={`${path.join(".")}:${index}`}
              path={[...path, index]}
              label={`[${index}]`}
              value={item}
              disabled={disabled}
              onReplace={(next) => {
                const draft = [...value];
                draft[index] = next;
                onReplace(draft);
              }}
            />
          ))}
        </div>
      </div>
    );
  }

  if (isJsonObject(value)) {
    const entries = Object.entries(value);
    return (
      <div className="json-node">
        {path.length > 0 ? <p className="json-node-label"><strong>{label}</strong></p> : null}
        <div className="json-node-children">
          {entries.map(([key, child]) => (
            <JsonNode
              key={`${path.join(".")}:${key}`}
              path={[...path, key]}
              label={key}
              value={child}
              disabled={disabled}
              onReplace={(next) => {
                onReplace({ ...value, [key]: next });
              }}
            />
          ))}
        </div>
      </div>
    );
  }

  return (
    <JsonPrimitiveField
      label={label}
      value={value}
      disabled={disabled}
      onChange={(next) => onReplace(next)}
    />
  );
}

function JsonPrimitiveField({
  label,
  value,
  disabled,
  onChange
}: {
  label: string;
  value: string | number | boolean | null;
  disabled?: boolean;
  onChange: (next: string | number | boolean | null) => void;
}) {
  if (typeof value === "boolean") {
    return (
      <label className="json-field">
        <span>{label}</span>
        <select
          value={String(value)}
          disabled={disabled}
          onChange={(event) => onChange(event.target.value === "true")}
        >
          <option value="true">true</option>
          <option value="false">false</option>
        </select>
      </label>
    );
  }

  if (typeof value === "number") {
    return (
      <label className="json-field">
        <span>{label}</span>
        <input
          type="number"
          value={Number.isFinite(value) ? String(value) : ""}
          disabled={disabled}
          onChange={(event) => {
            const parsed = Number(event.target.value);
            if (Number.isFinite(parsed)) onChange(parsed);
          }}
        />
      </label>
    );
  }

  if (value === null) {
    return (
      <label className="json-field">
        <span>{label}</span>
        <input
          type="text"
          placeholder="null"
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
        />
      </label>
    );
  }

  return (
    <label className="json-field">
      <span>{label}</span>
      <textarea
        value={value}
        disabled={disabled}
        rows={Math.max(2, Math.min(6, Math.ceil((value.length || 1) / 40)))}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function isJsonObject(value: JsonValue): value is { [key: string]: JsonValue } {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function normalizeJsonValue(value: unknown): JsonValue {
  if (value === null) return null;
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return value;
  if (Array.isArray(value)) return value.map((item) => normalizeJsonValue(item));
  if (typeof value === "object") {
    const output: Record<string, JsonValue> = {};
    for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
      output[key] = normalizeJsonValue(item);
    }
    return output;
  }
  return String(value);
}
