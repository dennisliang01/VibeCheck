"""Agent 5: Performance Expert - Anticipates scaling problems."""

import re
from typing import List, Dict, Any
from agents.base_agent import BaseAgent
from core.models import CodeFragment, AgentResult, AgentType, ValidationContext


class PerformanceExpert(BaseAgent):
    """Anticipates problems de scaling."""

    def __init__(self):
        super().__init__(AgentType.PERFORMANCE)

    def analyze(
        self, fragments: List[CodeFragment], context: ValidationContext
    ) -> AgentResult:
        """Analyze code for performance issues."""
        self.reset()

        # Check 1: Algorithmic complexity
        self._check_complexity(fragments)

        # Check 2: Call frequency estimation
        self._estimate_call_frequency(fragments, context)

        # Check 3: Memory allocation in loops
        self._check_memory_in_loops(fragments)

        # Check 4: Resource leaks
        self._check_resource_leaks(fragments)

        # Check 5: Blocking network calls
        self._check_blocking_calls(fragments)

        # Check 6: N+1 queries
        self._check_n_plus_one(fragments)

        # Check 7: Missing caching
        self._check_caching(fragments)

        # Check 8: Batch processing
        self._check_batch_processing(fragments)

        # Key question: when does this become a problem?
        self._estimate_breaking_point(fragments)

        score = self.calculate_score()

        return AgentResult(
            agent_type=self.agent_type,
            score=score,
            gaps=self.gaps,
            findings=self.findings,
            examples=self.examples,
            raw_analysis={
                "bottlenecks_found": len(
                    [f for f in self.findings if f["severity"] in ["critical", "high"]]
                ),
                "optimization_opportunities": len(self.examples),
                "estimated_breaking_point": self._get_breaking_point(fragments),
            },
        )

    def _check_complexity(self, fragments: List[CodeFragment]):
        """Check algorithmic complexity."""
        # Nested loops indicate O(n^2) or worse
        for fragment in fragments:
            if fragment.fragment_type == "function":
                content = fragment.content

                # Count nesting levels
                loop_patterns = [r"\bfor\b", r"\bwhile\b"]
                max_nesting = 0
                current_nesting = 0

                for line in content.split("\n"):
                    if any(re.search(p, line) for p in loop_patterns):
                        current_nesting += 1
                        max_nesting = max(max_nesting, current_nesting)
                    if "}" in line or line.strip().startswith("return"):
                        current_nesting = max(0, current_nesting - 1)

                if max_nesting >= 3:
                    self.add_finding(
                        description=f"Triple nested loops detected - O(n³) complexity",
                        severity="critical",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion="Refactor to reduce complexity, consider indexing or memoization",
                    )
                elif max_nesting == 2:
                    self.add_finding(
                        description=f"Nested loops detected - O(n²) complexity",
                        severity="high",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion="Consider if O(n²) is necessary, or use hash maps for O(n)",
                    )

    def _estimate_call_frequency(
        self, fragments: List[CodeFragment], context: ValidationContext
    ):
        """Estimate how often code will be called."""
        # Entry points are called frequently
        entry_point_patterns = [
            r"app\.(get|post|put|delete)",
            r"@app\.route",
            r"router\.(get|post)",
            r"exports\.(handler|main)",
            r"def\s+handler",
        ]

        for fragment in fragments:
            for pattern in entry_point_patterns:
                if re.search(pattern, fragment.content):
                    self.add_finding(
                        description=f"Entry point function - will be called frequently",
                        severity="info",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion="Ensure this code is optimized for high call frequency",
                    )

    def _check_memory_in_loops(self, fragments: List[CodeFragment]):
        """Check for memory allocation inside loops."""
        allocation_patterns = [
            r"new\s+\w+",
            r"\[\s*\]",  # Array literal
            r"\{\s*\}",  # Object literal
            r"Array\s*\(",
            r"Object\s*\(",
            r"list\s*\(",
            r"dict\s*\(",
        ]

        for fragment in fragments:
            if fragment.fragment_type == "function":
                lines = fragment.content.split("\n")
                in_loop = False
                loop_indent = 0

                for i, line in enumerate(lines):
                    # Detect loop start
                    if re.search(r"\b(for|while)\b", line):
                        in_loop = True
                        loop_indent = len(line) - len(line.lstrip())

                    # Detect loop end (simplified)
                    if (
                        in_loop
                        and line.strip()
                        and len(line) - len(line.lstrip()) <= loop_indent
                    ):
                        if not re.search(r"\b(for|while)\b", line):
                            in_loop = False

                    # Check for allocations inside loop
                    if in_loop:
                        for pattern in allocation_patterns:
                            if re.search(pattern, line):
                                self.add_finding(
                                    description=f"Memory allocation inside loop",
                                    severity="high",
                                    file=fragment.file_path,
                                    line=fragment.start_line + i,
                                    suggestion="Move allocation outside loop or use object pooling",
                                )
                                break

    def _check_resource_leaks(self, fragments: List[CodeFragment]):
        """Check for potential resource leaks."""
        resource_patterns = [
            (r"open\s*\(", r"close\s*\(", "File handle"),
            (r"connect\s*\(", r"disconnect|close\s*\(", "Connection"),
            (r"createConnection", r"end\s*\(|close\s*\(", "DB connection"),
            (r"addEventListener", r"removeEventListener", "Event listener"),
            (r"\.subscribe\(", r"\.unsubscribe\(", "Subscription"),
        ]

        for fragment in fragments:
            content = fragment.content
            for open_pat, close_pat, resource_type in resource_patterns:
                opens = len(re.findall(open_pat, content))
                closes = len(re.findall(close_pat, content))

                if opens > closes:
                    self.add_finding(
                        description=f"Potential {resource_type} leak: {opens} opens, {closes} closes",
                        severity="critical",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion=f"Use try/finally or context managers to ensure {resource_type}s are closed",
                    )

    def _check_blocking_calls(self, fragments: List[CodeFragment]):
        """Check for blocking network calls."""
        blocking_patterns = [
            r"requests\.(get|post|put|delete)\s*\(",
            r"urllib\.request",
            r"http\.get\s*\(",
            r"\.sync\s*\(",
            r"fs\.readFileSync",
            r"fs\.writeFileSync",
        ]

        async_patterns = [
            r"async\s+def",
            r"async\s+function",
            r"await\s+",
            r"\.then\s*\(",
            r"Promise",
        ]

        for fragment in fragments:
            has_blocking = any(
                re.search(p, fragment.content) for p in blocking_patterns
            )
            has_async = any(re.search(p, fragment.content) for p in async_patterns)

            if has_blocking and not has_async:
                self.add_finding(
                    description="Synchronous blocking call detected in potentially async context",
                    severity="high",
                    file=fragment.file_path,
                    line=fragment.start_line,
                    suggestion="Convert to async/await to prevent blocking the event loop",
                )

    def _check_n_plus_one(self, fragments: List[CodeFragment]):
        """Check for N+1 query patterns."""
        n_plus_one_patterns = [
            (
                r"for\s+\w+\s+in\s+\w+",
                r"\.(get|filter|find)\s*\(",
                "Loop with query inside",
            ),
            (r"\.map\s*\(", r"\.find\s*\(|\.get\s*\(", "Map with individual queries"),
        ]

        for fragment in fragments:
            content = fragment.content
            for loop_pat, query_pat, desc in n_plus_one_patterns:
                if re.search(loop_pat, content) and re.search(query_pat, content):
                    # Check if they're in close proximity
                    loop_pos = (
                        content.find("for")
                        if "for" in content
                        else content.find(".map")
                    )
                    query_pos = (
                        content.find(".get")
                        if ".get" in content
                        else content.find(".find")
                    )

                    if abs(loop_pos - query_pos) < 500:  # Within 500 chars
                        self.add_finding(
                            description=f"Potential N+1 query: {desc}",
                            severity="critical",
                            file=fragment.file_path,
                            line=fragment.start_line,
                            suggestion="Use JOIN, select_related, or DataLoader to batch queries",
                        )

                        self.add_example(
                            title="Fix N+1 with DataLoader",
                            code="""
# Instead of:
for user in users:
    orders = db.get_orders(user.id)  # N queries!

# Use:
user_ids = [u.id for u in users]
orders = db.get_orders_batch(user_ids)  # 1 query

# Or with DataLoader:
orders = await order_loader.load_many(user_ids)
""",
                            explanation="Batch queries to avoid N+1 problem",
                        )

    def _check_caching(self, fragments: List[CodeFragment]):
        """Check for missing caching opportunities."""
        cacheable_patterns = [
            r"def\s+get_",
            r"def\s+fetch_",
            r"function\s+get",
            r"function\s+fetch",
            r"API call",
            r"database",
            r"query",
        ]

        cache_patterns = [
            r"cache",
            r"@cached",
            r"@lru_cache",
            r"redis",
            r"memcached",
            r"Cache",
            r"\.memo",
            r"useMemo",
            r"useCallback",
        ]

        for fragment in fragments:
            looks_cacheable = any(
                re.search(p, fragment.content, re.IGNORECASE)
                for p in cacheable_patterns
            )
            has_caching = any(
                re.search(p, fragment.content, re.IGNORECASE) for p in cache_patterns
            )

            if looks_cacheable and not has_caching:
                # Check if it's an expensive operation
                expensive_indicators = [
                    "database",
                    "query",
                    "API",
                    "http",
                    "request",
                    "fetch",
                ]
                is_expensive = any(
                    ind in fragment.content.lower() for ind in expensive_indicators
                )

                if is_expensive:
                    self.add_finding(
                        description=f"Expensive operation without caching: '{fragment.metadata.get('name')}'",
                        severity="medium",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion="Add caching for frequently accessed, rarely changing data",
                    )

    def _check_batch_processing(self, fragments: List[CodeFragment]):
        """Check if batch processing is used instead of one-by-one."""
        one_by_one_patterns = [
            r"for\s+\w+\s+in\s+\w+\s*:\s*\n\s+\w+\.(create|insert|save|send)",
            r"\.forEach\s*\([^)]*=>\s*\{[^}]*\.(create|insert|save|send)",
        ]

        for fragment in fragments:
            for pattern in one_by_one_patterns:
                if re.search(pattern, fragment.content):
                    self.add_finding(
                        description="One-by-one processing detected - consider batching",
                        severity="medium",
                        file=fragment.file_path,
                        line=fragment.start_line,
                        suggestion="Use batch insert/update APIs for better performance",
                    )

    def _estimate_breaking_point(self, fragments: List[CodeFragment]):
        """Estimate when code becomes a problem."""
        # This is a heuristic based on patterns found
        pass

    def _get_breaking_point(self, fragments: List[CodeFragment]) -> str:
        """Get estimated breaking point."""
        critical_findings = [f for f in self.findings if f["severity"] == "critical"]
        high_findings = [f for f in self.findings if f["severity"] == "high"]

        if critical_findings:
            return "Will fail under moderate load (100s of requests)"
        elif high_findings:
            return "Will degrade under high load (1000s of requests)"
        elif self.findings:
            return "Will degrade under very high load (10k+ requests)"
        else:
            return "Should scale well to high load"
