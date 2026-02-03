"""
Tests for graph API: ensure site/academic companies are returned with company_type
so the frontend "Include Sites" filter can show them.
"""
import pytest
import sqlite3
import tempfile
from pathlib import Path

from app.services.sqlite_service import SQLiteService


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    yield path
    path.unlink(missing_ok=True)


@pytest.fixture
def sqlite_service(temp_db):
    """SQLiteService using temp DB with schema initialized."""
    return SQLiteService(db_path=temp_db)


@pytest.fixture
def graph_with_industry_and_site(sqlite_service, temp_db):
    """
    Insert minimal graph: one indication, one trial, one asset,
    two companies (industry lead sponsor + academic/site collaborator).
    """
    with sqlite_service.connection() as conn:
        c = conn.cursor()
        # Trial matching indication "Melanoma" (conditions_searchable used by graph query)
        c.execute(
            """
            INSERT INTO trials (trial_id, title, phase, status, conditions, conditions_searchable, evidence, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "NCT_TEST_SITES_001",
                "Test trial for sites",
                "PHASE2",
                "RECRUITING",
                "[\"Melanoma\"]",
                "melanoma",
                "[]",
                "2024-01-01T00:00:00",
            ),
        )
        # Industry company (lead sponsor)
        c.execute(
            """
            INSERT INTO companies (company_id, name, company_type, evidence, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("company_industry_1", "Test Pharma Inc", "industry", "[]", "2024-01-01T00:00:00"),
        )
        # Site/academic company (collaborator)
        c.execute(
            """
            INSERT INTO companies (company_id, name, company_type, evidence, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("company_site_1", "Test University Hospital", "academic", "[]", "2024-01-01T00:00:00"),
        )
        # Asset
        c.execute(
            """
            INSERT INTO assets (asset_id, name, evidence, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            ("asset_1", "Test Drug", "[]", "2024-01-01T00:00:00"),
        )
        # Industry is lead sponsor, site is collaborator
        c.execute(
            """
            INSERT INTO sponsors_trial (company_id, trial_id, role, evidence)
            VALUES (?, ?, ?, ?), (?, ?, ?, ?)
            """,
            (
                "company_industry_1",
                "NCT_TEST_SITES_001",
                "lead_sponsor",
                "[]",
                "company_site_1",
                "NCT_TEST_SITES_001",
                "collaborator",
                "[]",
            ),
        )
        # Asset has this trial
        c.execute(
            """
            INSERT INTO has_trial (asset_id, trial_id, evidence)
            VALUES (?, ?, ?)
            """,
            ("asset_1", "NCT_TEST_SITES_001", "[]"),
        )
        # Industry owns the asset (so we don't add DEVELOPS for them; OWNS only)
        c.execute(
            """
            INSERT INTO owns (company_id, asset_id, confidence, source, is_current, evidence)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("company_industry_1", "asset_1", 1.0, "inferred", 1, "[]"),
        )
    return sqlite_service


class TestGraphReturnsSiteCompanies:
    """Graph API must return site/academic companies with company_type so Include Sites works."""

    def test_get_indication_graph_returns_both_industry_and_site_companies(
        self, graph_with_industry_and_site
    ):
        """Response must include both industry and non-industry (site/academic) company nodes."""
        service = graph_with_industry_and_site
        result = service.get_indication_graph(
            ["Melanoma"],
            trial_filter="all",
            limit=100,
        )
        nodes = result["nodes"]
        company_nodes = [n for n in nodes if n.get("type") == "company"]
        assert len(company_nodes) >= 2, (
            "Graph should return at least 2 company nodes (industry + site). "
            f"Got {len(company_nodes)}: {[n.get('id') for n in company_nodes]}"
        )
        ids = {n["id"] for n in company_nodes}
        assert "company_industry_1" in ids, "Industry company should be in graph"
        assert "company_site_1" in ids, "Site/academic company should be in graph"

    def test_site_company_has_company_type_in_data(self, graph_with_industry_and_site):
        """Site company node must have data.company_type so frontend can filter (Include Sites)."""
        service = graph_with_industry_and_site
        result = service.get_indication_graph(
            ["Melanoma"],
            trial_filter="all",
            limit=100,
        )
        nodes = result["nodes"]
        site_node = next((n for n in nodes if n.get("id") == "company_site_1"), None)
        assert site_node is not None, "Site company node should be present"
        data = site_node.get("data") or {}
        company_type = data.get("company_type")
        assert company_type is not None, (
            "Site company node must have data.company_type (got None). "
            "Frontend uses this to show/hide when Include Sites is toggled."
        )
        assert company_type.lower() != "industry", (
            f"Site company should have company_type != 'industry' (got {company_type!r}). "
            "Include Sites OFF filters to industry only; site must be non-industry."
        )

    def test_industry_company_has_company_type_industry(self, graph_with_industry_and_site):
        """Industry company node must have data.company_type == 'industry'."""
        service = graph_with_industry_and_site
        result = service.get_indication_graph(
            ["Melanoma"],
            trial_filter="all",
            limit=100,
        )
        nodes = result["nodes"]
        industry_node = next((n for n in nodes if n.get("id") == "company_industry_1"), None)
        assert industry_node is not None, "Industry company node should be present"
        data = industry_node.get("data") or {}
        assert (data.get("company_type") or "").lower() == "industry", (
            f"Industry company should have data.company_type == 'industry' (got {data.get('company_type')!r})"
        )
