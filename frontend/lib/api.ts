import { API_BASE } from "./config";
import type { RiskResult } from "./types";

export class ApiError extends Error {
    constructor(
        message: string,
        public status: number,
    ) {
        super(message);
    }
}

/** Per-tool override: "on" forces invoke, "off" forces skip, absent = agent decides. */
export type ToolOverrides = Record<string, "on" | "off">;

export async function postQuery(
    query: string,
    toolOverrides?: ToolOverrides,
): Promise<RiskResult> {
    let res: Response;
    const body: Record<string, unknown> = { query };
    if (toolOverrides && Object.keys(toolOverrides).length > 0) {
        body.tool_overrides = toolOverrides;
    }
    try {
        res = await fetch(`${API_BASE}/query`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
    } catch {
        throw new ApiError(
            "Cannot reach the Argus API — is the backend running?",
            0,
        );
    }
    if (!res.ok) {
        let detail = `Request failed (HTTP ${res.status})`;
        try {
            const body = await res.json();
            if (body?.detail) detail = String(body.detail);
        } catch {
            /* non-JSON error body */
        }
        throw new ApiError(detail, res.status);
    }
    return (await res.json()) as RiskResult;
}
