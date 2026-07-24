from .generator import AttackGenerator, AttackPayload, AttackCategory
from .vault import AttackVault
from .mutations import MutationEngine
from .red_team_loop import RedTeamLoop, RedTeamResult, RedTeamReport
from .success_analyzer import (
    JudgeAnalysis,
    analyze_verdicts,
    judge_instability_rate,
    majority_vote,
    DEFAULT_JUDGE_SAMPLES,
    DEFAULT_INSTABILITY_THRESHOLD,
)
from .benchmark_catalog import (
    BENCHMARK_V2_CATEGORIES,
    BenchmarkCategory,
    benchmark_category_ids,
    compute_benchmark_coverage,
)
from .evals_ucs import (
    UCSScore,
    aggregate,
    refine_with_response,
    score_hit,
    score_http_mark,
)

# Harness (Planner-Executor HTTP loop)
from .target_http import HitResult, KrepostHttpTarget
from .feedback import FeedbackEntry, OperatorTrace, hit_to_feedback, hit_to_trace
from .planner_types import PlannedAttack, PlannerInput, PlannerOutput
from .planner import StubPlanner
from .recipe_executor import build_batch, build_payload_from_recipe
from .adversarial_loop import AdversarialLoop, AdversarialReport

# Auth subsystem (5-level) — optional deps: pyotp, argon2-cffi ([planner] extra)
try:
    from .auth import (
        CapabilityLevel,
        PlannerCapabilities,
        AuthManager,
        init_secrets_dir,
        generate_ingest_token,
    )
except ImportError:  # pragma: no cover
    CapabilityLevel = None  # type: ignore
    PlannerCapabilities = None  # type: ignore
    AuthManager = None  # type: ignore
    init_secrets_dir = None  # type: ignore
    generate_ingest_token = None  # type: ignore

# Sealed envelopes (Round Table / SealedRedLoop — payload stays on Air)
from .sealed import SealedEnvelope, SealedStore, attack_id_for
