const compact = new Intl.NumberFormat("en", {
    notation: "compact",
    maximumFractionDigits: 2,
});
const plain = new Intl.NumberFormat("en");

/** 2460555 → "2.46M" */
export const fmtCompact = (n: number): string => compact.format(n);

/** 2460555 → "2,460,555" */
export const fmtInt = (n: number): string => plain.format(n);

/** 8660 → "8.7s" · 541 → "541ms" */
export const fmtMs = (ms: number): string =>
    ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`;

/** 1584893.2 → "$1.58M" */
export const fmtMoney = (n: number): string => `$${compact.format(n)}`;
