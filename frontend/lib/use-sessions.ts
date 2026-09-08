"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { RiskResult, Session, SessionRun } from "./types";

const STORAGE_KEY = "argus.sessions.v1";

/** All session state lives in ONE object. Keeping sessions / activeSessionId /
 * activeRunId as separate useStates let them desync (a run could be added
 * against an id that no longer matched any session, silently vanishing). */
type State = {
    sessions: Session[];
    activeSessionId: string;
    activeRunId: string | null;
};

function newSession(index: number): Session {
    return {
        id:
            typeof crypto !== "undefined" && crypto.randomUUID
                ? crypto.randomUUID()
                : `s_${Date.now()}_${Math.random().toString(36).slice(2)}`,
        name: `Session ${index}`,
        createdAt: Date.now(),
        runs: [],
    };
}

function freshState(): State {
    const s = newSession(1);
    return { sessions: [s], activeSessionId: s.id, activeRunId: null };
}

function loadState(): State {
    try {
        const raw = window.localStorage.getItem(STORAGE_KEY);
        if (raw) {
            const p = JSON.parse(raw) as Partial<State>;
            if (p.sessions?.length) {
                const activeSessionId =
                    p.sessions.find((s) => s.id === p.activeSessionId)?.id ??
                    p.sessions[0].id;
                return { sessions: p.sessions, activeSessionId, activeRunId: null };
            }
        }
    } catch {
        /* corrupt or unavailable storage — start fresh */
    }
    return freshState();
}

export function useSessions() {
    // empty on the server; hydrated from storage after mount (no SSR mismatch)
    const [state, setState] = useState<State>({
        sessions: [],
        activeSessionId: "",
        activeRunId: null,
    });
    const hydrated = useRef(false);

    useEffect(() => {
        setState(loadState());
        hydrated.current = true;
    }, []);

    // persist — never before hydration, and never an empty session list
    useEffect(() => {
        if (!hydrated.current || state.sessions.length === 0) return;
        try {
            window.localStorage.setItem(
                STORAGE_KEY,
                JSON.stringify({
                    sessions: state.sessions,
                    activeSessionId: state.activeSessionId,
                }),
            );
        } catch {
            /* storage full / disabled — non-fatal */
        }
    }, [state]);

    const startNewSession = useCallback(() => {
        setState((prev) => {
            const s = newSession(prev.sessions.length + 1);
            return {
                sessions: [s, ...prev.sessions],
                activeSessionId: s.id,
                activeRunId: null,
            };
        });
    }, []);

    /** Add a completed run to the active session. Self-healing: if the active
     * id somehow matches nothing, it targets the first session (creating one if
     * needed) so a result can never be silently dropped. */
    const addRun = useCallback((query: string, result: RiskResult) => {
        const run: SessionRun = {
            id: result.run_id,
            query,
            startedAt: Date.now(),
            result,
        };
        setState((prev) => {
            const sessions = prev.sessions.length ? prev.sessions : [newSession(1)];
            const targetId = sessions.some((s) => s.id === prev.activeSessionId)
                ? prev.activeSessionId
                : sessions[0].id;
            return {
                sessions: sessions.map((s) =>
                    s.id === targetId ? { ...s, runs: [run, ...s.runs] } : s,
                ),
                activeSessionId: targetId,
                activeRunId: run.id,
            };
        });
    }, []);

    const selectRun = useCallback((sessionId: string, runId: string) => {
        setState((prev) => ({
            ...prev,
            activeSessionId: sessionId,
            activeRunId: runId,
        }));
    }, []);

    const deleteRun = useCallback((sessionId: string, runId: string) => {
        setState((prev) => ({
            ...prev,
            sessions: prev.sessions.map((s) =>
                s.id === sessionId
                    ? { ...s, runs: s.runs.filter((r) => r.id !== runId) }
                    : s,
            ),
            activeRunId: prev.activeRunId === runId ? null : prev.activeRunId,
        }));
    }, []);

    /** Delete a session; never leaves the app session-less. */
    const deleteSession = useCallback((sessionId: string) => {
        setState((prev) => {
            const remaining = prev.sessions.filter((s) => s.id !== sessionId);
            const sessions = remaining.length ? remaining : [newSession(1)];
            const activeSessionId =
                prev.activeSessionId === sessionId ? sessions[0].id : prev.activeSessionId;
            return {
                sessions,
                activeSessionId,
                activeRunId:
                    prev.activeSessionId === sessionId ? null : prev.activeRunId,
            };
        });
    }, []);

    const activeSession =
        state.sessions.find((s) => s.id === state.activeSessionId) ?? null;
    const activeRun =
        activeSession?.runs.find((r) => r.id === state.activeRunId) ?? null;

    return {
        sessions: state.sessions,
        activeSession,
        activeSessionId: state.activeSessionId,
        activeRun,
        activeRunId: state.activeRunId,
        startNewSession,
        addRun,
        selectRun,
        deleteRun,
        deleteSession,
    };
}
