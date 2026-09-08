from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Runtime configuration, loaded from environment / backend/.env.

    Every value has a sensible local default so a fresh clone runs with zero
    setup beyond `pip install` — only the OpenRouter key is required, and only
    for the agent endpoints.
    """

    # LLM (agent intent parsing + synthesis) — via OpenRouter
    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemini-2.5-flash"

    # Audit store: SQLite by default (zero-setup); point at Postgres in prod,
    # e.g. postgresql+psycopg://user:pass@host/argus — no code change needed.
    database_url: str = f"sqlite:///{BACKEND_DIR / 'argus.db'}"

    # Dataset (gitignored; sourced from Kaggle — see README)
    data_path_override: Path | None = None
    accounts_path_override: Path | None = None
    patterns_path_override: Path | None = None

    _KAGGLE_DATASET = "ealtman2019/ibm-transactions-for-anti-money-laundering-aml"

    @property
    def data_path(self) -> Path:
        """Resolve the transactions CSV — local override, or kagglehub download.

        NOTE: reaching the kagglehub branch triggers a network download. Never
        call this from a liveness path (see `dataset_available`).
        """
        if self.data_path_override:
            return self.data_path_override
        import kagglehub

        return Path(
            kagglehub.dataset_download(self._KAGGLE_DATASET, path="HI-Small_Trans.csv")
        )

    @property
    def accounts_path(self) -> Path:
        if self.accounts_path_override:
            return self.accounts_path_override
        import kagglehub

        return Path(
            kagglehub.dataset_download(self._KAGGLE_DATASET, path="HI-Small_accounts.csv")
        )

    @property
    def patterns_path(self) -> Path:
        if self.patterns_path_override:
            return self.patterns_path_override
        import kagglehub

        return Path(
            kagglehub.dataset_download(self._KAGGLE_DATASET, path="HI-Small_Patterns.txt")
        )

    def dataset_available(self) -> bool:
        """Cheap presence check for /health — NEVER downloads.

        If a local override is set, checks the file exists. Otherwise reports
        whether kagglehub has already cached the dataset, without fetching it.
        """
        if self.data_path_override:
            return Path(self.data_path_override).exists()
        # kagglehub caches under ~/.cache/kagglehub — presence there means ready
        cache = Path.home() / ".cache" / "kagglehub" / "datasets" / self._KAGGLE_DATASET
        return cache.exists()

    # Parquet caches built on first load (gitignored)
    cache_dir: Path = BACKEND_DIR / "data"

    # Sampling: keep every transaction touching a laundering-involved account,
    # plus the FULL histories of a deterministic fraction of remaining accounts
    # (account-level sampling preserves the behavioural sequences that
    # velocity / rolling-sum features depend on).
    sample_account_fraction: float = 0.25

    # CORS — the Next.js dev server
    cors_origins: list[str] = ["http://localhost:3000"]

    # .env.local (gitignored, personal) overrides .env when both exist
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env", BACKEND_DIR / ".env.local"),
        env_file_encoding="utf-8",
    )


settings = Settings()
