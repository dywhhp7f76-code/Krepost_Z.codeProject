# Предложение 07: Sovereign Execution Brokers (SEB)

## Что

Интеграция архитектуры Sovereign Execution Brokers (SEB) в Крепость для создания runtime enforcement boundary между фазами proposal/admission/execution агентов. SEB обеспечивает certificate-bound контроль прав на мутации инфраструктуры, revocation сертификатов и полный audit trail.

Источник: [Sovereign Execution Brokers: Certificate-Bound Authority in Agentic Control Planes](https://arxiv.org/abs/2606.20520v1)

## Зачем

### Проблема

Текущая SecurityPipeline Крепости проверяет **входящие запросы** (injection, PII, attack vectors), но не контролирует **что агент делает после получения GREEN-вердикта**:

- Агент с GREEN-вердиктом может модифицировать конфигурации, код, данные
- Нет механизма отзыва прав агента в реальном времени (revocation)
- Self-improvement цикл создаёт риск неконтролируемой самомодификации
- Отсутствует audit trail на уровне отдельных мутаций

### Что решает SEB

SEB вводит три чётко разделённые фазы для каждой мутации:

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   PROPOSAL    │───>│   ADMISSION   │───>│  EXECUTION   │
│               │    │               │    │               │
│ Агент         │    │ Broker        │    │ Runtime       │
│ предлагает    │    │ проверяет     │    │ выполняет     │
│ мутацию       │    │ сертификат    │    │ под контролем │
│               │    │ + scope       │    │               │
└──────────────┘    └──────────────┘    └──────────────┘
```

| Возможность | Без SEB | С SEB |
|---|---|---|
| Контроль мутаций | Нет (post-hoc логи) | Pre-execution admission |
| Идентификация агента | session_id | Certificate-bound identity |
| Отзыв прав | Перезапуск сервиса | Мгновенная revocation сертификата |
| Аудит | Логи запросов | Полный trail: proposal -> admission -> execution -> result |
| Scope ограничения | Нет | Сертификат определяет разрешённые ресурсы/операции |
| Самомодификация | Неконтролируемая | Требует admission с elevated certificate |

### Критичность для Крепости

1. **Self-improvement** -- агенты Крепости модифицируют свой код. SEB гарантирует, что каждая модификация проходит через admission с валидным сертификатом.
2. **Multi-agent** -- несколько агентов работают параллельно. Каждый имеет свой сертификат с ограниченным scope.
3. **Red-teaming** -- red-team агент имеет расширенные права. SEB позволяет выдать temporary certificate с чётким scope и автоматическим отзывом.
4. **Compliance** -- полный audit trail для каждой мутации, необходимый для анализа инцидентов.
5. **Принцип минимальных привилегий** -- SecurityPipeline не должен иметь доступ к ChromaDB напрямую (только через FewShotMatcher); SMART_CACHE не должен модифицировать TrustRegistry. Сертификаты формализуют эти ограничения.
6. **Изоляция при компрометации** -- если атакующий обходит Layer 2, он получает доступ только к полномочиям GuardClassifier, а не ко всей системе.

## Что добавляется

### Архитектура SEB в Крепости

```
┌─────────────────────────────────────────────────────────────────┐
│                      Krepost Agent Layer                         │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Agent A   │  │ Agent B   │  │ RedTeam   │  │ SelfImpr │       │
│  │ cert:rw   │  │ cert:ro   │  │ cert:atk  │  │ cert:evo │       │
│  │ scope:    │  │ scope:    │  │ scope:    │  │ scope:   │       │
│  │  cache/*  │  │  cache/*  │  │  test/*   │  │  code/*  │       │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬────┘       │
│        │             │             │             │              │
│        └─────────────┴──────┬──────┴─────────────┘              │
│                             │                                    │
│                    ┌────────v────────┐                           │
│                    │  Proposal Gate   │                           │
│                    │  (MutationReq)   │                           │
│                    └────────┬────────┘                           │
│                             │                                    │
│  ┌──────────────────────────v──────────────────────────────┐    │
│  │              Sovereign Execution Broker                   │    │
│  │                                                           │    │
│  │  ┌─────────────────┐  ┌───────────────┐  ┌───────────┐  │    │
│  │  │ CertValidator    │  │ ScopeChecker   │  │ AuditLog  │  │    │
│  │  │                  │  │                │  │           │  │    │
│  │  │ verify_cert()    │  │ check_scope()  │  │ log()     │  │    │
│  │  │ check_revoked()  │  │ check_resource │  │ query()   │  │    │
│  │  │ check_expiry()   │  │ check_action   │  │ export()  │  │    │
│  │  └────────┬─────────┘  └───────┬────────┘  └─────┬─────┘  │    │
│  │           │                    │                  │        │    │
│  │           └────────────────────┼──────────────────┘        │    │
│  │                                │                           │    │
│  │                    ┌───────────v───────────┐               │    │
│  │                    │   AdmissionDecision    │               │    │
│  │                    │   ALLOW / DENY / DEFER │               │    │
│  │                    └───────────┬───────────┘               │    │
│  └────────────────────────────────┼───────────────────────────┘    │
│                                   │                                │
│                          ┌────────v────────┐                       │
│                          │ Execution Layer  │                       │
│                          │ (controlled)     │                       │
│                          └─────────────────┘                       │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │              SecurityPipeline v2.2                         │     │
│  │  L1 Regex -> L2 Guard -> L3 FewShot -> L4 Output          │     │
│  │  (входной контроль запросов -- без изменений)              │     │
│  └──────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

### Матрица разрешений компонентов Крепости

```yaml
# krepost/security/permissions.yaml

components:
  SecurityPipeline:
    allowed:
      - action: "classify"
        resource: "user_input"
      - action: "read"
        resource: "regex_patterns"
      - action: "invoke"
        resource: "GuardClassifier"
      - action: "invoke"
        resource: "FewShotMatcher"
      - action: "invoke"
        resource: "OutputFilter"
    denied:
      - action: "write"
        resource: "trust_registry"
      - action: "direct_access"
        resource: "chromadb"

  SMART_CACHE:
    allowed:
      - action: "read_write"
        resource: "cache_layers"
      - action: "read"
        resource: "embeddings"
    denied:
      - action: "modify"
        resource: "security_pipeline"
      - action: "access"
        resource: "trust_registry"

  RedTeamAgent:
    allowed:
      - action: "attack"
        resource: "test/*"
      - action: "read"
        resource: "pipeline/config"
    denied:
      - action: "write"
        resource: "production/*"
      - action: "modify"
        resource: "trust_registry"

  SelfImprovementAgent:
    allowed:
      - action: "modify_self"
        resource: "code/*"
    denied:
      - action: "modify"
        resource: "security/pipeline.py"  # требует DEFER
```

### Эскиз кода: Certificate Validation

```python
# krepost/security/sovereign_broker.py (эскиз)
"""
Sovereign Execution Broker (SEB) для Крепости.
Runtime enforcement boundary: proposal -> admission -> execution.

Ref: arXiv:2606.20520
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import secrets
import fnmatch
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path

from loguru import logger


# ════════════════════════════════════════════════════════════
# СЕРТИФИКАТЫ
# ════════════════════════════════════════════════════════════

class CertificateScope(str, Enum):
    """Разрешённые области действия агента."""
    READ_CACHE = "cache:read"
    WRITE_CACHE = "cache:write"
    READ_CONFIG = "config:read"
    WRITE_CONFIG = "config:write"
    READ_CODE = "code:read"
    WRITE_CODE = "code:write"
    EXECUTE_TOOL = "tool:execute"
    RED_TEAM = "redteam:attack"
    SELF_MODIFY = "evolution:modify"


class AdmissionDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    DEFER = "defer"  # Требуется human-in-the-loop


@dataclass
class AgentCertificate:
    """
    Сертификат агента -- привязывает identity к разрешённым действиям.

    Свойства:
    - Ограниченный срок жизни (expires_at)
    - Scope -- набор разрешённых действий
    - Привязка к ресурсам (resource_patterns -- glob patterns)
    - Revocable -- может быть отозван мгновенно
    - Подписан HMAC-SHA256 ключом Broker'а
    """
    cert_id: str
    agent_id: str
    agent_name: str
    issued_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    scopes: Set[CertificateScope] = field(default_factory=set)
    resource_patterns: List[str] = field(default_factory=list)
    max_mutations: int = 100
    mutations_used: int = 0
    revoked: bool = False
    revoked_reason: str = ""
    signature: str = ""

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    @property
    def is_valid(self) -> bool:
        return (not self.revoked
                and not self.is_expired
                and self.mutations_used < self.max_mutations)

    @property
    def remaining_mutations(self) -> int:
        return max(0, self.max_mutations - self.mutations_used)

    def to_dict(self) -> dict:
        return {
            "cert_id": self.cert_id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "scopes": [s.value for s in self.scopes],
            "resource_patterns": self.resource_patterns,
            "max_mutations": self.max_mutations,
            "mutations_used": self.mutations_used,
            "revoked": self.revoked,
        }


@dataclass
class MutationProposal:
    """Предложение мутации от агента."""
    proposal_id: str
    agent_id: str
    cert_id: str
    action: str                       # "write", "delete", "execute", "modify"
    resource: str                     # Целевой ресурс (путь, ключ, команда)
    payload: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    justification: str = ""           # Обоснование мутации от агента


@dataclass
class AuditEntry:
    """Запись в audit log."""
    entry_id: str
    timestamp: float
    proposal: MutationProposal
    decision: AdmissionDecision
    reason: str
    cert_snapshot: dict
    execution_result: Optional[str] = None
    execution_error: Optional[str] = None


# ════════════════════════════════════════════════════════════
# ВАЛИДАЦИЯ СЕРТИФИКАТОВ
# ════════════════════════════════════════════════════════════

class CertificateValidator:
    """
    Валидатор сертификатов агентов.

    Проверяет:
    1. Подпись (HMAC-SHA256)
    2. Срок действия
    3. Revocation status (CRL)
    4. Лимит мутаций
    """

    def __init__(self, signing_key: bytes):
        self._signing_key = signing_key
        self._revocation_list: Set[str] = set()

    def sign_certificate(self, cert: AgentCertificate) -> str:
        """Подписать сертификат ключом Broker'а."""
        payload = json.dumps({
            "cert_id": cert.cert_id,
            "agent_id": cert.agent_id,
            "scopes": sorted(s.value for s in cert.scopes),
            "resource_patterns": cert.resource_patterns,
            "expires_at": cert.expires_at,
            "max_mutations": cert.max_mutations,
        }, sort_keys=True)

        signature = hmac.new(
            self._signing_key,
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        cert.signature = signature
        return signature

    def verify_signature(self, cert: AgentCertificate) -> bool:
        """Верифицировать подпись сертификата."""
        payload = json.dumps({
            "cert_id": cert.cert_id,
            "agent_id": cert.agent_id,
            "scopes": sorted(s.value for s in cert.scopes),
            "resource_patterns": cert.resource_patterns,
            "expires_at": cert.expires_at,
            "max_mutations": cert.max_mutations,
        }, sort_keys=True)

        expected = hmac.new(
            self._signing_key,
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(cert.signature, expected)

    def validate(self, cert: AgentCertificate) -> Tuple[bool, str]:
        """
        Полная валидация сертификата.

        Возвращает (valid, reason).
        """
        # 1. Подпись
        if not self.verify_signature(cert):
            return False, "invalid_signature"

        # 2. Revocation
        if cert.cert_id in self._revocation_list:
            return False, "revoked_by_crl"
        if cert.revoked:
            return False, f"revoked: {cert.revoked_reason}"

        # 3. Срок действия
        if cert.is_expired:
            return False, "expired"

        # 4. Лимит мутаций
        if cert.mutations_used >= cert.max_mutations:
            return False, "mutation_limit_exceeded"

        return True, "valid"

    def revoke(self, cert_id: str, reason: str = "") -> None:
        """Отозвать сертификат (добавить в CRL)."""
        self._revocation_list.add(cert_id)
        logger.warning(f"Certificate revoked: {cert_id} (reason: {reason})")

    def is_revoked(self, cert_id: str) -> bool:
        return cert_id in self._revocation_list


# ════════════════════════════════════════════════════════════
# SCOPE CHECKER
# ════════════════════════════════════════════════════════════

class ScopeChecker:
    """Проверка scope сертификата против запрошенной мутации."""

    ACTION_SCOPE_MAP: Dict[str, Set[CertificateScope]] = {
        "read": {CertificateScope.READ_CACHE,
                 CertificateScope.READ_CONFIG,
                 CertificateScope.READ_CODE},
        "write": {CertificateScope.WRITE_CACHE,
                  CertificateScope.WRITE_CONFIG,
                  CertificateScope.WRITE_CODE},
        "delete": {CertificateScope.WRITE_CACHE,
                   CertificateScope.WRITE_CONFIG,
                   CertificateScope.WRITE_CODE},
        "execute": {CertificateScope.EXECUTE_TOOL},
        "invoke": {CertificateScope.EXECUTE_TOOL},
        "classify": {CertificateScope.EXECUTE_TOOL},
        "attack": {CertificateScope.RED_TEAM},
        "modify_self": {CertificateScope.SELF_MODIFY},
    }

    @staticmethod
    def check_scope(
        cert: AgentCertificate, proposal: MutationProposal
    ) -> Tuple[bool, str]:
        """Проверить, имеет ли сертификат scope для данной мутации."""
        required = ScopeChecker.ACTION_SCOPE_MAP.get(proposal.action, set())
        if not required:
            return False, f"unknown_action: {proposal.action}"

        matching = cert.scopes & required
        if not matching:
            return False, (f"insufficient_scope: need one of "
                           f"{[s.value for s in required]}")

        if not ScopeChecker._match_resource(
            cert.resource_patterns, proposal.resource
        ):
            return False, f"resource_not_in_scope: {proposal.resource}"

        return True, "scope_ok"

    @staticmethod
    def _match_resource(patterns: List[str], resource: str) -> bool:
        """Проверить, попадает ли ресурс под паттерны сертификата."""
        for pattern in patterns:
            if fnmatch.fnmatch(resource, pattern):
                return True
        return False


# ════════════════════════════════════════════════════════════
# SOVEREIGN EXECUTION BROKER
# ════════════════════════════════════════════════════════════

class SovereignExecutionBroker:
    """
    Главный Broker: proposal -> admission -> execution.

    Использование:
        broker = SovereignExecutionBroker(signing_key=os.urandom(32))

        # Выдать сертификат агенту
        cert = broker.issue_certificate(
            agent_id="agent_alpha",
            agent_name="Cache Manager",
            scopes={CertificateScope.READ_CACHE,
                    CertificateScope.WRITE_CACHE},
            resource_patterns=["cache/*"],
            ttl_seconds=3600,
        )

        # Агент предлагает мутацию
        proposal = MutationProposal(
            proposal_id="mut_001",
            agent_id="agent_alpha",
            cert_id=cert.cert_id,
            action="write",
            resource="cache/l2/entry_42",
            payload={"data": "..."},
        )

        # Broker проверяет и допускает/отклоняет
        decision, reason = broker.admit(proposal, cert)
        # decision: ALLOW / DENY / DEFER
    """

    def __init__(
        self,
        signing_key: bytes,
        audit_path: Path = Path("data/audit/seb_audit.jsonl"),
        require_human_for: Optional[Set[CertificateScope]] = None,
    ):
        self._validator = CertificateValidator(signing_key)
        self._certificates: Dict[str, AgentCertificate] = {}
        self._audit_log: List[AuditEntry] = []
        self._audit_path = audit_path
        self._audit_path.parent.mkdir(parents=True, exist_ok=True)

        # Scopes, требующие human-in-the-loop
        self._require_human = require_human_for or {
            CertificateScope.SELF_MODIFY,
            CertificateScope.WRITE_CODE,
        }

    def issue_certificate(
        self,
        agent_id: str,
        agent_name: str,
        scopes: Set[CertificateScope],
        resource_patterns: List[str],
        ttl_seconds: float = 3600.0,
        max_mutations: int = 100,
    ) -> AgentCertificate:
        """Выдать новый сертификат агенту."""
        cert = AgentCertificate(
            cert_id=f"cert_{agent_id}_{secrets.token_hex(8)}",
            agent_id=agent_id,
            agent_name=agent_name,
            scopes=scopes,
            resource_patterns=resource_patterns,
            expires_at=time.time() + ttl_seconds,
            max_mutations=max_mutations,
        )
        self._validator.sign_certificate(cert)
        self._certificates[cert.cert_id] = cert

        logger.info(
            f"Certificate issued: {cert.cert_id} for {agent_name} "
            f"(scopes={[s.value for s in scopes]}, "
            f"ttl={ttl_seconds}s, max_mutations={max_mutations})"
        )
        return cert

    def revoke_certificate(self, cert_id: str, reason: str = "manual") -> bool:
        """Отозвать сертификат."""
        cert = self._certificates.get(cert_id)
        if cert is None:
            logger.error(f"Certificate not found: {cert_id}")
            return False

        cert.revoked = True
        cert.revoked_reason = reason
        self._validator.revoke(cert_id, reason)
        logger.warning(
            f"Certificate revoked: {cert_id} ({cert.agent_name}), "
            f"reason: {reason}"
        )
        return True

    def admit(
        self, proposal: MutationProposal, cert: AgentCertificate
    ) -> Tuple[AdmissionDecision, str]:
        """
        Вынести admission decision по proposal.

        Этапы:
        1. Валидность сертификата (подпись, expiry, revocation, лимиты)
        2. Scope сертификата (action + resource)
        3. Human-in-the-loop для опасных операций
        """
        # 1. Валидация сертификата
        valid, reason = self._validator.validate(cert)
        if not valid:
            decision = AdmissionDecision.DENY
            self._record_audit(proposal, decision,
                               f"cert_invalid: {reason}", cert)
            logger.warning(f"DENY {proposal.proposal_id}: "
                           f"cert invalid ({reason})")
            return decision, reason

        # 2. Проверка scope
        scope_ok, scope_reason = ScopeChecker.check_scope(cert, proposal)
        if not scope_ok:
            decision = AdmissionDecision.DENY
            self._record_audit(proposal, decision,
                               f"scope_denied: {scope_reason}", cert)
            logger.warning(f"DENY {proposal.proposal_id}: {scope_reason}")
            return decision, scope_reason

        # 3. Human-in-the-loop для опасных операций
        required = ScopeChecker.ACTION_SCOPE_MAP.get(proposal.action, set())
        if required & self._require_human:
            decision = AdmissionDecision.DEFER
            self._record_audit(proposal, decision,
                               "requires_human_approval", cert)
            logger.info(
                f"DEFER {proposal.proposal_id}: requires human approval "
                f"(action={proposal.action}, resource={proposal.resource})"
            )
            return decision, "requires_human_approval"

        # 4. Допустить мутацию
        cert.mutations_used += 1
        decision = AdmissionDecision.ALLOW
        self._record_audit(proposal, decision, "admitted", cert)
        logger.info(
            f"ALLOW {proposal.proposal_id}: "
            f"{proposal.action} on {proposal.resource} "
            f"(cert={cert.cert_id}, "
            f"mutations={cert.mutations_used}/{cert.max_mutations})"
        )
        return decision, "admitted"

    def record_execution(
        self, proposal: MutationProposal,
        success: bool, error: str = ""
    ) -> None:
        """Записать результат выполнения мутации в audit."""
        for entry in reversed(self._audit_log):
            if entry.proposal.proposal_id == proposal.proposal_id:
                entry.execution_result = "success" if success else "failure"
                entry.execution_error = error if error else None
                self._flush_audit_entry(entry)
                break

    def _record_audit(
        self, proposal: MutationProposal,
        decision: AdmissionDecision, reason: str,
        cert: AgentCertificate,
    ) -> None:
        """Записать в audit log."""
        entry = AuditEntry(
            entry_id=f"audit_{int(time.time()*1000)}_{secrets.token_hex(4)}",
            timestamp=time.time(),
            proposal=proposal,
            decision=decision,
            reason=reason,
            cert_snapshot=cert.to_dict(),
        )
        self._audit_log.append(entry)
        self._flush_audit_entry(entry)

    def _flush_audit_entry(self, entry: AuditEntry) -> None:
        """Записать audit entry в JSONL файл."""
        try:
            record = {
                "entry_id": entry.entry_id,
                "timestamp": entry.timestamp,
                "timestamp_iso": datetime.fromtimestamp(
                    entry.timestamp, tz=timezone.utc
                ).isoformat(),
                "proposal": {
                    "id": entry.proposal.proposal_id,
                    "agent_id": entry.proposal.agent_id,
                    "cert_id": entry.proposal.cert_id,
                    "action": entry.proposal.action,
                    "resource": entry.proposal.resource,
                    "justification": entry.proposal.justification,
                },
                "decision": entry.decision.value,
                "reason": entry.reason,
                "cert_snapshot": entry.cert_snapshot,
                "execution_result": entry.execution_result,
                "execution_error": entry.execution_error,
            }
            with open(self._audit_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit: {e}")

    def get_audit_trail(
        self, agent_id: Optional[str] = None, limit: int = 100
    ) -> List[dict]:
        """Получить audit trail."""
        entries = self._audit_log
        if agent_id:
            entries = [e for e in entries
                       if e.proposal.agent_id == agent_id]
        return [
            {
                "entry_id": e.entry_id,
                "timestamp_iso": datetime.fromtimestamp(
                    e.timestamp, tz=timezone.utc
                ).isoformat(),
                "agent_id": e.proposal.agent_id,
                "action": e.proposal.action,
                "resource": e.proposal.resource,
                "decision": e.decision.value,
                "reason": e.reason,
            }
            for e in entries[-limit:]
        ]

    @property
    def stats(self) -> dict:
        active = [c for c in self._certificates.values() if c.is_valid]
        return {
            "total_certificates": len(self._certificates),
            "active_certificates": len(active),
            "revoked_certificates": sum(
                1 for c in self._certificates.values() if c.revoked
            ),
            "total_audit_entries": len(self._audit_log),
            "decisions": {
                "allow": sum(1 for e in self._audit_log
                             if e.decision == AdmissionDecision.ALLOW),
                "deny": sum(1 for e in self._audit_log
                            if e.decision == AdmissionDecision.DENY),
                "defer": sum(1 for e in self._audit_log
                             if e.decision == AdmissionDecision.DEFER),
            },
        }
```

### Интеграция с SecurityPipeline

```python
# Изменения в krepost/security/pipeline.py

class SecurityPipeline:
    def __init__(self, ...,
                 broker: Optional[SovereignExecutionBroker] = None):
        # ... существующая инициализация ...
        self.broker = broker

    async def process_with_broker(
        self,
        text: str,
        session_id: str,
        cert: AgentCertificate,
        mutation_action: str = "execute",
        mutation_resource: str = "pipeline/process",
    ) -> SecurityContext:
        """
        Обработка запроса с проверкой через SEB.
        Агент должен предъявить валидный сертификат.
        """
        if self.broker:
            proposal = MutationProposal(
                proposal_id=f"pipe_{session_id}_{int(time.time()*1000)}",
                agent_id=cert.agent_id,
                cert_id=cert.cert_id,
                action=mutation_action,
                resource=mutation_resource,
                justification=f"Pipeline process for session {session_id}",
            )

            decision, reason = self.broker.admit(proposal, cert)

            if decision == AdmissionDecision.DENY:
                ctx = SecurityContext(
                    session_id=session_id, user_input=text)
                ctx.is_compromised = True
                ctx.verdict = "RED"
                ctx.violation_layer = "SEB"
                ctx.attack_vector = f"certificate_denied: {reason}"
                return ctx

            if decision == AdmissionDecision.DEFER:
                ctx = SecurityContext(
                    session_id=session_id, user_input=text)
                ctx.verdict = "YELLOW"
                ctx.metadata["seb_defer"] = reason
                return ctx

        # Стандартная обработка при ALLOW
        ctx = await self.process(text, session_id)

        if self.broker:
            self.broker.record_execution(
                proposal,
                success=(ctx.verdict != "RED"),
                error=ctx.attack_vector if ctx.verdict == "RED" else "",
            )

        return ctx
```

## Зависимости

| Зависимость | Назначение | Статус |
|---|---|---|
| hmac + hashlib (stdlib) | Подпись/верификация сертификатов | Встроенные |
| fnmatch (stdlib) | Проверка resource patterns | Встроенный |
| loguru | Логирование | Уже используется |
| pyyaml | Чтение матрицы разрешений | Может потребоваться установка |
| SecurityPipeline v2.2 | Базовый пайплайн | Уже развёрнут |
| JSONL audit storage | Хранение audit trail | Файловая система |

Новых тяжёлых зависимостей **не требуется** (только pyyaml для permissions.yaml).

## Риски

| Риск | Уровень | Митигация |
|---|---|---|
| HMAC ключ хранится в памяти процесса | Средний | Загрузка из secure keychain/env; ротация ключей; в перспективе -- HSM |
| Overhead на admission check (~1-3ms на операцию) | Низкий | In-memory проверки; при 4 слоях pipeline +4-12ms total -- приемлемо |
| Ошибка в матрице разрешений блокирует легитимные операции | Средний | Fail-closed by design; DEFER вместо DENY для human-in-the-loop; тестирование матрицы |
| Рассогласование audit log при crash | Средний | Flush на каждую запись; WAL для критичных операций |
| Ротация сертификатов добавляет operational complexity | Низкий | Auto-rotate с grace period |
| Рост audit log | Низкий | Ротация по размеру/времени; архивация в SQLite |

## Этапы внедрения

1. **Фаза 1: Core** -- CertificateValidator + ScopeChecker + AuditLog (standalone)
2. **Фаза 2: Broker** -- SovereignExecutionBroker с интеграцией в SecurityPipeline
3. **Фаза 3: Permissions** -- матрица разрешений для всех компонентов Крепости
4. **Фаза 4: Agent certificates** -- выдача сертификатов каждому агенту
5. **Фаза 5: Human-in-the-loop** -- Telegram/UI для approval DEFER решений
6. **Фаза 6: Analytics** -- дашборд audit trail, anomaly detection на паттернах мутаций

## Ссылки

- [arXiv:2606.20520](https://arxiv.org/abs/2606.20520v1) -- Sovereign Execution Brokers: Certificate-Bound Authority in Agentic Control Planes
- foundation/2026-06-19: "runtime enforcement boundary (SEB) для агентов: верифицирует сертификаты на мутации, scoped identity, revocation, audit-логи"
- foundation/2026-06-22: "отделяет proposal/admission/execution, выдаёт short-lived revocable execution identity, проверяет сертификаты перед мутацией. Тестировано на AWS/Kubernetes."

## Статус: ⏳ Ожидает одобрения
